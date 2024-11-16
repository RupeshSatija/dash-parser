// MPD Parser
document.getElementById('parseMpdBtn').addEventListener('click', async () => {
    const mpdUrl = document.getElementById('mpdUrl').value;
    const resultDiv = document.getElementById('mpdResult');

    if (!mpdUrl) {
        resultDiv.innerHTML = '<div class="alert alert-danger">Please enter an MPD URL</div>';
        return;
    }

    try {
        resultDiv.innerHTML = '<div class="spinner-border text-primary" role="status"></div>';

        const response = await fetch('/parse-mpd', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ url: mpdUrl })
        });

        const data = await response.json();
        
        if (!response.ok) {
            throw new Error(data.error || 'Failed to parse MPD');
        }

        if (data.periods.length === 0) {
            resultDiv.innerHTML = '<div class="alert alert-info">No encrypted periods found in the MPD.</div>';
            return;
        }

        let html = '<div class="mt-3">';
        
        if (data.allPeriodsSame) {
            html += `
                <div class="alert alert-info">
                    Showing Period 1 of ${data.totalPeriods} periods. All periods share the same encryption information.
                </div>
            `;
        }

        data.periods.forEach((period, periodIndex) => {
            html += `
                <div class="card mb-3">
                    <div class="card-header">Period ${periodIndex + 1}</div>
                    <div class="card-body">
                        <div class="table-responsive">
                            <table class="table table-striped">
                                <thead>
                                    <tr>
                                        <th>Type</th>
                                        <th>MPD Key ID</th>
                                        <th>Init Segment Key ID</th>
                                        <th>Status</th>
                                        <th>Bandwidth</th>
                                        <th>Resolution</th>
                                        <th>Codecs</th>
                                    </tr>
                                </thead>
                                <tbody>
                                    ${period.tracks.map(track => {
                                        const keyIdsMatch = track.mpdKeyId.toLowerCase() === track.initKeyId.toLowerCase();
                                        const validationClass = keyIdsMatch ? 'success' : 'danger';
                                        const validationIcon = keyIdsMatch ? '✓' : '✗';
                                        
                                        return `
                                            <tr>
                                                <td>${track.type}</td>
                                                <td><code>${track.mpdKeyId}</code></td>
                                                <td><code>${track.initKeyId || 'Not available'}</code></td>
                                                <td>
                                                    <span class="badge bg-${validationClass}">
                                                        ${validationIcon} ${keyIdsMatch ? 'Match' : 'Mismatch'}
                                                    </span>
                                                </td>
                                                <td>${track.bandwidth}</td>
                                                <td>${track.type === 'video' ? track.resolution : 'N/A'}</td>
                                                <td>${track.codecs}</td>
                                            </tr>
                                        `;
                                    }).join('')}
                                </tbody>
                            </table>
                        </div>
                    </div>
                </div>
            `;
        });
        html += '</div>';
        resultDiv.innerHTML = html;

    } catch (error) {
        resultDiv.innerHTML = `<div class="alert alert-danger">${error.message}</div>`;
    }
});

// Copy Init URL functionality
document.addEventListener('click', (e) => {
    if (e.target.classList.contains('copy-init-url')) {
        const url = e.target.dataset.url;
        document.getElementById('initUrl').value = url;
    }
}); 