document.addEventListener('DOMContentLoaded', () => {
    const omniInput = document.getElementById('omniInput');
    const scanBtn = document.getElementById('scanBtn');
    const loading = document.getElementById('loading');
    const resultsSection = document.getElementById('resultsSection');
    const dashboardGrid = document.getElementById('dashboardGrid');
    const targetBadge = document.getElementById('targetBadge');
    const omniContainer = document.querySelector('.omni-search-container');

    scanBtn.addEventListener('click', performScan);
    omniInput.addEventListener('keypress', (e) => {
        if (e.key === 'Enter') performScan();
    });

    const exifUpload = document.getElementById('exifUpload');
    if (exifUpload) {
        exifUpload.addEventListener('change', async (e) => {
            const file = e.target.files[0];
            if (!file) return;
            
            // Show loading state
            omniContainer.classList.add('scanned');
            loading.classList.remove('hidden');
            resultsSection.classList.add('hidden');
            dashboardGrid.innerHTML = '';
            scanBtn.disabled = true;
            targetBadge.textContent = `IMAGE: ${file.name}`;
            
            const formData = new FormData();
            formData.append('image', file);
            
            try {
                const response = await fetch('/api/osint/exif', {
                    method: 'POST',
                    body: formData
                });
                
                const result = await response.json();
                loading.classList.add('hidden');
                scanBtn.disabled = false;
                
                if (!response.ok || !result.ok) {
                    renderError(result.error || 'Failed to extract EXIF data');
                } else {
                    renderResults(result);
                }
            } catch (error) {
                loading.classList.add('hidden');
                scanBtn.disabled = false;
                renderError('Network error connecting to Omni-Scanner engine.');
            }
            
            // Reset the input
            exifUpload.value = '';
        });
    }

    async function performScan() {
        const query = omniInput.value.trim();
        if (!query) return;

        // UI State: Loading
        omniContainer.classList.add('scanned');
        loading.classList.remove('hidden');
        resultsSection.classList.add('hidden');
        dashboardGrid.innerHTML = '';
        scanBtn.disabled = true;

        try {
            const response = await fetch('/api/osint/scan', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ query })
            });

            const result = await response.json();
            
            if (response.ok) {
                renderResults(result);
            } else {
                renderError(result.error || 'Scan failed.');
            }
        } catch (error) {
            renderError('Backend server is offline or unreachable.');
        } finally {
            loading.classList.add('hidden');
            scanBtn.disabled = false;
        }
    }

    function renderError(msg) {
        targetBadge.textContent = 'ERROR';
        targetBadge.style.color = 'var(--neon-red)';
        targetBadge.style.borderColor = 'var(--neon-red)';
        
        dashboardGrid.innerHTML = `
            <div class="intel-card" style="border-color: var(--neon-red);">
                <h3><i class="fa-solid fa-triangle-exclamation" style="color: var(--neon-red);"></i> Error</h3>
                <div class="intel-value" style="font-size: 1rem; color: var(--neon-red);">${msg}</div>
            </div>
        `;
        resultsSection.classList.remove('hidden');
    }

    function renderResults(data) {
        targetBadge.textContent = `${data.type}: ${data.target}`;
        targetBadge.style.color = 'var(--neon-blue)';
        targetBadge.style.borderColor = 'var(--neon-blue)';

        let html = '';

        if (data.type === 'IP') {
            const d = data.data;
            if (d.error) {
                renderError(d.error);
                return;
            }
            html += createCard('fa-location-dot', 'Location', d.location);
            html += createCard('fa-map', 'Coordinates', d.coordinates);
            html += createCard('fa-network-wired', 'ISP', d.isp);
            html += createCard('fa-building', 'Organization', d.organization);
            html += createCard('fa-clock', 'Timezone', d.timezone);
        } 
        else if (data.type === 'PHONE') {
            const d = data.data;
            if (d.error) {
                renderError(d.error);
                return;
            }
            html += createCard('fa-phone', 'Intl Format', d.number);
            html += createCard('fa-earth-americas', 'Country Code', `+${d.country_code}`);
            html += createCard('fa-location-dot', 'Location', d.location);
            html += createCard('fa-sim-card', 'Carrier', d.carrier);
            html += createCard('fa-clock', 'Timezones', d.timezones.join(', '));
        }
        else if (data.type === 'EMAIL') {
            const d = data.data;
            if (d.error) {
                renderError(d.error);
                return;
            }
            
            // Domain Info
            html += createCard('fa-at', 'Domain', d.domain_info.domain);
            html += createCard(d.domain_info.is_disposable ? 'fa-trash' : 'fa-server', 'Provider Type', d.domain_info.is_disposable ? 'Disposable / Burner' : d.domain_info.provider);
            
            // Gravatar
            if (d.gravatar && d.gravatar.has_profile) {
                html += `
                    <div class="intel-card" style="border-color: var(--neon-blue);">
                        <h3><i class="fa-solid fa-image"></i> Gravatar Profile</h3>
                        <div class="intel-value" style="display:flex; justify-content:center; align-items:center;">
                            <img src="${d.gravatar.url}" style="border-radius: 50%; width: 100px; height: 100px; border: 2px solid var(--neon-blue);" alt="Gravatar">
                        </div>
                    </div>
                `;
            } else {
                html += createCard('fa-image-portrait', 'Gravatar', 'No profile picture linked.');
            }
            
            // Username Correlation
            if (d.social_profiles && d.social_profiles.length > 0) {
                const profiles = d.social_profiles;
                let profilesHtml = '<div class="profile-grid">';
                
                profiles.forEach(p => {
                    const icon = p.found ? 'fa-check' : 'fa-xmark';
                    const statusClass = p.found ? 'found' : 'not-found';
                    const link = p.found ? `<a href="${p.url}" target="_blank">${p.platform} <i class="fa-solid fa-arrow-up-right-from-square" style="font-size: 0.7rem;"></i></a>` : p.platform;
                    
                    profilesHtml += `
                        <div class="profile-item ${statusClass}">
                            <i class="fa-solid ${icon}"></i>
                            ${link}
                        </div>
                    `;
                });
                profilesHtml += '</div>';

                html += `
                    <div class="intel-card" style="grid-column: 1 / -1;">
                        <h3><i class="fa-solid fa-users-viewfinder"></i> Username Correlation (@${d.username})</h3>
                        ${profilesHtml}
                    </div>
                `;
            }
        }
        else if (data.type === 'USERNAME') {
            const profiles = data.data.profiles || [];
            let profilesHtml = '<div class="profile-grid">';
            
            profiles.forEach(p => {
                const icon = p.found ? 'fa-check' : 'fa-xmark';
                const statusClass = p.found ? 'found' : 'not-found';
                const link = p.found ? `<a href="${p.url}" target="_blank">${p.platform} <i class="fa-solid fa-arrow-up-right-from-square" style="font-size: 0.7rem;"></i></a>` : p.platform;
                
                profilesHtml += `
                    <div class="profile-item ${statusClass}">
                        <i class="fa-solid ${icon}"></i>
                        ${link}
                    </div>
                `;
            });
            profilesHtml += '</div>';

            html += `
                <div class="intel-card" style="grid-column: 1 / -1;">
                    <h3><i class="fa-solid fa-users-viewfinder"></i> Cross-Platform Presence</h3>
                    ${profilesHtml}
                </div>
            `;
        }
        else if (data.type === 'EXIF') {
            const d = data.data;
            if (d.error) {
                renderError(d.error);
                return;
            }
            if (d.Make) html += createCard('fa-camera', 'Make', d.Make);
            if (d.Model) html += createCard('fa-mobile-screen', 'Model', d.Model);
            if (d.OriginalTime) html += createCard('fa-clock', 'Taken On', d.OriginalTime);
            if (d.Software) html += createCard('fa-code', 'Software', d.Software);
            
            if (d.GPS) {
                html += `
                    <div class="intel-card" style="grid-column: 1 / -1; border-color: var(--neon-green);">
                        <h3><i class="fa-solid fa-map-location-dot" style="color: var(--neon-green);"></i> Exact GPS Location</h3>
                        <div class="intel-value" style="font-size: 1.1rem; color: var(--neon-green);">
                            Lat: ${d.GPS.Latitude}, Lon: ${d.GPS.Longitude}
                            <a href="${d.GPS.MapLink}" target="_blank" style="margin-left: 10px; color: #fff; text-decoration: underline;">Open in Maps <i class="fa-solid fa-arrow-up-right-from-square"></i></a>
                        </div>
                    </div>
                `;
            }
        }
        else {
            html += createCard('fa-info-circle', 'Status', data.data.message || 'Data unavailable');
        }

        dashboardGrid.innerHTML = html;
        resultsSection.classList.remove('hidden');
    }

    function createCard(icon, title, value) {
        return `
            <div class="intel-card">
                <h3><i class="fa-solid ${icon}"></i> ${title}</h3>
                <div class="intel-value">${value}</div>
            </div>
        `;
    }
});
