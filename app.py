import logging
import os
import re
import subprocess
import tempfile
import xml.etree.ElementTree as ET

import requests
from flask import Flask, jsonify, render_template, request

# Configure logging
logging.basicConfig(
    level=logging.DEBUG, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

app = Flask(__name__)


def parse_init_segment(data):
    """Parse MP4 init segment to extract key ID using mp4info"""
    temp_path = None
    try:
        logger.info("Starting init segment parsing")
        logger.info(f"Received init segment data of size: {len(data)} bytes")

        # Save init segment to temporary file
        with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as temp_file:
            temp_file.write(data)
            temp_path = temp_file.name

        logger.info(f"Saved init segment to temporary file: {temp_path}")

        # Run mp4info command
        cmd = ["mp4info", "--verbose", temp_path]
        logger.info(f"Executing command: {' '.join(cmd)}")
        result = subprocess.run(cmd, capture_output=True, text=True)

        if result.returncode != 0:
            logger.error(
                f"mp4info command failed with return code: {result.returncode}"
            )
            logger.error(f"mp4info stderr: {result.stderr}")
            return None

        # Parse output to find key ID
        output = result.stdout
        logger.debug(f"mp4info output length: {len(output)} bytes")
        logger.debug("Searching for default_KID in mp4info output")

        key_id_match = re.search(r"default_KID = \[(.*?)\]", output)

        if key_id_match:
            # Convert space-separated hex to continuous string
            key_id = key_id_match.group(1).replace(" ", "")
            logger.info(f"Successfully extracted key ID: {key_id}")
            return key_id

        logger.warning("No default_KID pattern found in mp4info output")
        logger.debug("First 500 chars of mp4info output for debugging:")
        logger.debug(output[:500])
        return None

    except Exception:
        logger.error("Exception occurred during init segment parsing", exc_info=True)
        return None
    finally:
        # Clean up temp file
        if temp_path:
            try:
                logger.debug(f"Attempting to delete temporary file: {temp_path}")
                os.unlink(temp_path)
                logger.debug("Successfully deleted temporary file")
            except Exception:
                logger.error(
                    f"Failed to delete temporary file: {temp_path}", exc_info=True
                )


def get_base_url_chain(element, ns, root=None):
    """Get BaseURL element from the MPD"""
    base_urls = []

    # Check root level first if provided
    if root is not None:
        root_base_url = root.find("dash:BaseURL", ns)
        if root_base_url is not None:
            logger.debug(f"Found root BaseURL: {root_base_url.text}")
            base_urls.append(root_base_url.text)

    # Then check element level
    element_base_url = element.find(".//dash:BaseURL", ns)
    if element_base_url is not None:
        logger.debug(f"Found element BaseURL: {element_base_url.text}")
        base_urls.append(element_base_url.text)

    if not base_urls:
        logger.debug("No BaseURL found")
    return base_urls


def get_absolute_url(base_url, relative_url, base_url_chain=None):
    logger.debug(f"Input - base_url: {base_url}")
    logger.debug(f"Input - relative_url: {relative_url}")
    logger.debug(f"Input - base_url_chain: {base_url_chain}")

    if relative_url.startswith("http://") or relative_url.startswith("https://"):
        logger.debug(f"Returning absolute URL as-is: {relative_url}")
        return relative_url

    # Get the domain from the MPD URL
    domain = "/".join(base_url.split("/")[:3])  # Gets https://domain.com
    logger.debug(f"Extracted domain: {domain}")

    # If we have a BaseURL from MPD, use it with domain
    if base_url_chain and base_url_chain[0]:
        # BaseURL is absolute path from domain root
        base_path = base_url_chain[0].strip("/")
        final_url = f"{domain}/{base_path}/{relative_url.lstrip('/')}"
        logger.debug(f"Using BaseURL chain - Final URL: {final_url}")
        return final_url

    # Fallback to MPD URL base
    base_parts = base_url.rsplit("/", 1)
    base_path = base_parts[0] if len(base_parts) > 1 else base_url
    final_url = f"{base_path.rstrip('/')}/{relative_url.lstrip('/')}"
    logger.debug(f"Using MPD URL base - Final URL: {final_url}")
    return final_url


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/parse-mpd", methods=["POST"])
def parse_mpd():
    try:
        url = request.json.get("url")
        if not url:
            return jsonify({"error": "URL is required"}), 400

        response = requests.get(url)
        response.raise_for_status()

        root = ET.fromstring(response.content)
        ns = {"dash": "urn:mpeg:dash:schema:mpd:2011", "cenc": "urn:mpeg:cenc:2013"}
        periods = []
        found_encrypted_period = False

        for period in root.findall(".//dash:Period", ns):
            if found_encrypted_period:
                break

            period_data = {"tracks": []}
            period_has_encryption = False

            for adaptation_set in period.findall(".//dash:AdaptationSet", ns):
                content_protection = adaptation_set.find(
                    ".//dash:ContentProtection[@cenc:default_KID]", ns
                )

                if content_protection is not None:
                    period_has_encryption = True
                    found_encrypted_period = True
                    content_type = (
                        adaptation_set.get("contentType")
                        or adaptation_set.get("mimeType", "").split("/")[0]
                    )

                    mpd_key_id = content_protection.get(
                        "{urn:mpeg:cenc:2013}default_KID"
                    )
                    mpd_key_id = re.sub(r"[^a-fA-F0-9]", "", mpd_key_id)

                    # Get BaseURL from adaptation set or period level, including root
                    base_url_chain = get_base_url_chain(adaptation_set, ns, root)
                    if not base_url_chain:
                        base_url_chain = get_base_url_chain(period, ns, root)

                    # Process all representations in this adaptation set
                    for representation in adaptation_set.findall(
                        ".//dash:Representation", ns
                    ):
                        bandwidth = representation.get("bandwidth")
                        width = representation.get("width", "N/A")
                        height = representation.get("height", "N/A")
                        codecs = representation.get("codecs", "N/A")

                        init_template = representation.find(
                            ".//dash:SegmentTemplate", ns
                        )

                        if init_template is not None and init_template.get(
                            "initialization"
                        ):
                            init_url = init_template.get("initialization")
                            init_url = init_url.replace(
                                "$RepresentationID$", representation.get("id", "")
                            )
                            init_url = get_absolute_url(url, init_url, base_url_chain)
                        else:
                            init_url = "Not available"

                        # Parse init segment for each representation
                        init_key_id = None
                        if init_url != "Not available":
                            try:
                                logger.info(f"Fetching init segment from: {init_url}")
                                init_response = requests.get(init_url)
                                init_response.raise_for_status()
                                init_key_id = parse_init_segment(init_response.content)
                                if init_key_id is None:
                                    init_key_id = "No key ID found"
                            except Exception as e:
                                logger.error(f"Failed to parse init segment: {str(e)}")
                                init_key_id = f"Failed to parse: {str(e)}"

                        period_data["tracks"].append(
                            {
                                "type": content_type,
                                "mpdKeyId": mpd_key_id,
                                "initKeyId": init_key_id,
                                "bandwidth": f"{int(bandwidth)/1000:.0f}kbps"
                                if bandwidth
                                else "N/A",
                                "resolution": f"{width}x{height}"
                                if width != "N/A"
                                else "N/A",
                                "codecs": codecs,
                            }
                        )

            if period_has_encryption:
                periods.append(period_data)

        return jsonify({"periods": periods})

    except requests.RequestException as e:
        return jsonify({"error": f"Failed to fetch MPD: {str(e)}"}), 500
    except Exception as e:
        return jsonify({"error": f"Failed to parse MPD: {str(e)}"}), 500


@app.route("/parse-init", methods=["POST"])
def parse_init():
    try:
        url = request.json.get("url")
        if not url:
            return jsonify({"error": "URL is required"}), 400

        response = requests.get(url)
        response.raise_for_status()

        key_id = parse_init_segment(response.content)
        if not key_id:
            return jsonify({"error": "No key ID found in init segment"}), 404

        return jsonify({"keyId": key_id})

    except requests.RequestException as e:
        return jsonify({"error": f"Failed to fetch init segment: {str(e)}"}), 500
    except Exception as e:
        return jsonify({"error": f"Failed to parse init segment: {str(e)}"}), 500


if __name__ == "__main__":
    app.run(host="0.0.0.0", debug=True)
