document.addEventListener('DOMContentLoaded', () => {
    let currentProfileData = null;
    let activePlatform = 'instagram';
    
    const searchForm = document.getElementById('search-form');
    const handleInput = document.getElementById('handle-input');
    const searchBtn = document.getElementById('search-btn');
    const btnText = searchBtn.querySelector('.btn-text');
    const btnLoader = searchBtn.querySelector('.btn-loader');
    

    
    const errorContainer = document.getElementById('error-container');
    const dashboard = document.getElementById('dashboard');
    
    // Profile Header Elements
    const profileHandle = document.getElementById('profile-handle');
    const profileName = document.getElementById('profile-name');
    const profileBio = document.getElementById('profile-bio');
    const profileTopics = document.getElementById('profile-topics');
    const profileLink = document.getElementById('profile-link');
    const profileSource = document.getElementById('profile-source');
    const inputPrefixIcon = document.getElementById('input-prefix-icon');
    
    // Stats Elements
    const statFollowers = document.getElementById('stat-followers');
    const statER = document.getElementById('stat-er');
    const erContext = document.getElementById('er-context');
    

    
    // Container Elements
    const postsContainer = document.getElementById('posts-container');
    


    // API Base URL (FastAPI) - dynamic based on local vs deployed environment
    const isLocal = window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1';
    const API_BASE = isLocal 
        ? 'http://localhost:8000/api' 
        : 'https://wittyfluence-api.onrender.com/api';

    const platformPlaceholders = {
        instagram: 'Enter Instagram handle or profile link (e.g. nasa, instagram.com/nasa)',
        youtube: 'Enter YouTube channel handle or link (e.g. @mkbhd, youtube.com/@mkbhd)',
        twitter: 'Enter X/Twitter handle or link (e.g. @elonmusk, x.com/elonmusk)'
    };

    // Custom Dropdown Selector Helpers
    function selectPlatform(platform) {
        activePlatform = platform;
        
        const option = document.querySelector(`.select-dropdown-option[data-value="${platform}"]`);
        if (option) {
            document.querySelectorAll('.select-dropdown-option').forEach(opt => opt.classList.remove('selected'));
            option.classList.add('selected');
            
            const svgIcon = option.querySelector('svg').outerHTML;
            const text = option.querySelector('span').textContent;
            
            document.getElementById('trigger-icon').innerHTML = svgIcon;
            document.getElementById('trigger-text').textContent = text;
        }
        
        handleInput.placeholder = platformPlaceholders[activePlatform];
        updatePrefixIcon();
    }

    const selectWrapper = document.getElementById('custom-select-wrapper');
    const selectTrigger = document.getElementById('select-trigger');
    
    selectTrigger.addEventListener('click', (e) => {
        e.stopPropagation();
        selectWrapper.classList.toggle('open');
    });
    
    document.addEventListener('click', () => {
        selectWrapper.classList.remove('open');
    });

    document.querySelectorAll('.select-dropdown-option').forEach(option => {
        option.addEventListener('click', (e) => {
            e.stopPropagation();
            const val = option.getAttribute('data-value');
            selectPlatform(val);
            selectWrapper.classList.remove('open');
        });
    });

    // Auto-detect platform from URLs
    handleInput.addEventListener('input', () => {
        const val = handleInput.value.trim().toLowerCase();
        let detectedPlatform = null;
        
        if (val.includes('instagram.com')) detectedPlatform = 'instagram';
        else if (val.includes('youtube.com') || val.includes('youtu.be')) detectedPlatform = 'youtube';
        else if (val.includes('twitter.com') || val.includes('x.com')) detectedPlatform = 'twitter';
        
        if (detectedPlatform && detectedPlatform !== activePlatform) {
            selectPlatform(detectedPlatform);
        }
        updatePrefixIcon();
    });

    function updatePrefixIcon() {
        const val = handleInput.value.trim();
        if (val.startsWith('http://') || val.startsWith('https://') || val.includes('.com') || val.includes('.be')) {
            inputPrefixIcon.style.display = 'none';
            handleInput.style.paddingLeft = '1.25rem';
        } else {
            inputPrefixIcon.style.display = 'block';
            handleInput.style.paddingLeft = '2.5rem';
            
            if (activePlatform === 'youtube' || activePlatform === 'twitter') {
                inputPrefixIcon.textContent = '@';
            } else {
                inputPrefixIcon.textContent = '@';
            }
        }
    }




    // Form Submission
    searchForm.addEventListener('submit', (e) => {
        e.preventDefault();
        const handle = handleInput.value.trim();
        if (handle) {
            triggerSearch(handle);
        }
    });

    function showLoading() {
        btnText.classList.add('hidden');
        btnLoader.classList.remove('hidden');
        searchBtn.disabled = true;
        errorContainer.classList.add('hidden');
    }

    function hideLoading() {
        btnText.classList.remove('hidden');
        btnLoader.classList.add('hidden');
        searchBtn.disabled = false;
    }

    function showError(msg) {
        errorContainer.textContent = msg;
        errorContainer.classList.remove('hidden');
        dashboard.classList.add('hidden');
    }

    // Main search routine
    async function triggerSearch(handle) {
        showLoading();
        
        try {
            const res = await fetch(`${API_BASE}/analyze/${encodeURIComponent(handle)}?platform=${activePlatform}`);
            if (!res.ok) {
                const errData = await res.json();
                throw new Error(errData.detail || 'Failed to fetch profile analysis.');
            }
            
            const data = await res.json();
            renderDashboard(data);
        } catch (err) {
            console.error(err);
            let errMsg = err.message || 'Server error. Make sure backend is running on port 8000.';
            if (window.location.protocol === 'https:' && (err.name === 'TypeError' || err.message.includes('Failed to fetch') || err.message.includes('fetch'))) {
                errMsg = 'Connection to local backend (http://localhost:8000) failed. Since this page is loaded over HTTPS, modern browsers block insecure HTTP requests to localhost (Mixed Content). To resolve this, run the app locally by visiting http://localhost:8000/ in your browser, or enable "Insecure content" in this site\'s browser settings.';
            }
            showError(errMsg);
        } finally {
            hideLoading();
        }
    }

    function formatNumber(num) {
        if (num >= 1000000) {
            return (num / 1000000).toFixed(1) + 'M';
        }
        if (num >= 1000) {
            return (num / 1000).toFixed(1) + 'K';
        }
        return num.toString();
    }

    const platformNames = {
        instagram: 'Instagram',
        youtube: 'YouTube',
        twitter: 'Twitter'
    };

    const platformConfigs = {
        instagram: {
            mediaCardTitle: '📷 Post Metrics (Images)',
            mediaAvgLikes: 'Avg. Likes',
            mediaAvgComments: 'Avg. Comments',
            mediaERLabel: 'Engagement Rate',
            videoCardTitle: '🎥 Reel Metrics (Videos)',
            videoAvgLikes: 'Avg. Likes',
            videoAvgComments: 'Avg. Comments',
            videoAvgViews: 'Avg. Views',
            videoRatio: 'Views to Followers',
            videoERLabel: 'Engagement Rate',
            mainERLabel: 'Engagement Rate',
            followersLabel: 'Followers'
        },
        youtube: {
            mediaCardTitle: '🎥 Video Metrics',
            mediaAvgLikes: 'Avg. Views',
            mediaAvgComments: 'Avg. Comments',
            mediaERLabel: 'Views/Subs Ratio',
            videoCardTitle: '🩳 Shorts Metrics',
            videoAvgLikes: 'Avg. Views',
            videoAvgComments: 'Avg. Comments',
            videoAvgViews: 'Avg. Views',
            videoRatio: 'Views to Subscribers',
            videoERLabel: 'Views/Subs Ratio',
            mainERLabel: 'Views/Subs Ratio',
            followersLabel: 'Subscribers'
        },
        twitter: {
            mediaCardTitle: '🐦 Tweets',
            mediaAvgLikes: 'Avg. Likes',
            mediaAvgComments: 'Avg. Replies',
            mediaERLabel: 'Engagement Rate',
            videoCardTitle: '🎥 Media Tweets',
            videoAvgLikes: 'Avg. Likes',
            videoAvgComments: 'Avg. Replies',
            videoAvgViews: 'Avg. Views',
            videoRatio: 'Impressions to Followers',
            videoERLabel: 'Engagement Rate',
            mainERLabel: 'Engagement Rate',
            followersLabel: 'Followers'
        }
    };

    function renderDashboard(data) {
        currentProfileData = data;
        
        // Show Dashboard Container
        dashboard.classList.remove('hidden');
        
        // Set dynamic theme styling class
        dashboard.className = 'dashboard';
        if (data.platform) {
            dashboard.classList.add(`theme-${data.platform}`);
        }
        
        // 1. Profile Header
        const avatarContainer = document.getElementById('profile-avatar-container');
        if (data.profile_pic_url) {
            avatarContainer.innerHTML = `<img src="${data.profile_pic_url}" alt="${data.full_name}'s avatar">`;
            avatarContainer.style.display = 'block';
        } else {
            avatarContainer.style.display = 'none';
        }

        profileHandle.textContent = `@${data.handle}`;
        profileName.textContent = data.full_name;
        profileBio.textContent = data.biography;
        // Construct actual platform profile link
        let profileUrl = '#';
        if (data.platform === 'instagram') {
            profileUrl = `https://www.instagram.com/${data.handle}/`;
        } else if (data.platform === 'youtube') {
            profileUrl = data.handle.startsWith('@') 
                ? `https://www.youtube.com/${data.handle}` 
                : `https://www.youtube.com/@${data.handle}`;
        } else if (data.platform === 'twitter') {
            profileUrl = `https://x.com/${data.handle}`;
        }
        profileLink.href = profileUrl;
        
        const visitBtnText = document.getElementById('visit-btn-text');
        if (visitBtnText) {
            visitBtnText.textContent = `Visit ${platformNames[data.platform] || 'Instagram'}`;
        }
        
        if (data.is_simulated) {
            profileSource.textContent = 'Demo Mode (Mirror Offline)';
            profileSource.className = 'source-badge simulated';
        } else if (data.is_estimated) {
            profileSource.textContent = 'Live Posts (Stats Est.)';
            profileSource.className = 'source-badge estimated';
        } else {
            profileSource.textContent = 'Live Data';
            profileSource.className = 'source-badge live';
        }
        
        profileTopics.innerHTML = '';

        // 2. Platform specific text configurations
        const config = platformConfigs[data.platform] || platformConfigs.instagram;
        document.getElementById('media-card-title').textContent = config.mediaCardTitle;
        document.getElementById('media-avg-likes-label').textContent = config.mediaAvgLikes;
        document.getElementById('media-avg-comments-label').textContent = config.mediaAvgComments;
        document.getElementById('media-er-label').textContent = config.mediaERLabel;

        document.getElementById('video-card-title').textContent = config.videoCardTitle;
        document.getElementById('video-avg-likes-label').textContent = config.videoAvgLikes;
        document.getElementById('video-avg-comments-label').textContent = config.videoAvgComments;
        document.getElementById('video-avg-views-label').textContent = config.videoAvgViews || 'Avg. Views';
        document.getElementById('video-er-label').textContent = config.videoERLabel;
        document.getElementById('video-ratio-label').textContent = config.videoRatio;
        
        document.getElementById('followers-stat-label').textContent = config.followersLabel;
        document.getElementById('stat-er-label').textContent = config.mainERLabel;

        // Toggle redundancy and views row visibility
        const ratioRow = document.getElementById('video-ratio-row');
        const mediaCommentsRow = document.getElementById('media-comments-row');
        const videoCommentsRow = document.getElementById('video-comments-row');
        const videoViewsRow = document.getElementById('video-views-row');
        
        if (data.platform === 'youtube') {
            ratioRow.classList.add('hidden');
            mediaCommentsRow.classList.add('hidden');
            videoCommentsRow.classList.add('hidden');
            videoViewsRow.classList.add('hidden');
        } else if (data.platform === 'twitter') {
            ratioRow.classList.remove('hidden');
            mediaCommentsRow.classList.remove('hidden');
            videoCommentsRow.classList.remove('hidden');
            videoViewsRow.classList.add('hidden');
        } else if (data.platform === 'instagram') {
            ratioRow.classList.add('hidden');
            mediaCommentsRow.classList.remove('hidden');
            videoCommentsRow.classList.remove('hidden');
            videoViewsRow.classList.add('hidden');
        } else {
            ratioRow.classList.remove('hidden');
            mediaCommentsRow.classList.remove('hidden');
            videoCommentsRow.classList.remove('hidden');
            videoViewsRow.classList.remove('hidden');
        }

        // 3. Stats Cards
        statFollowers.textContent = data.followers > 0 ? formatNumber(data.followers) : 'N/A';
        statER.textContent = data.followers > 0 ? `${data.avg_engagement_rate}%` : 'N/A';
        
        // Quality Contexts
        if (data.followers > 0) {
            const highThreshold = data.platform === 'youtube' ? 15.0 : 4.0;
            const avgThreshold = data.platform === 'youtube' ? 5.0 : 2.0;
            if (data.avg_engagement_rate > highThreshold) {
                erContext.textContent = data.platform === 'youtube' ? 'High View Velocity' : 'High Engagement';
                erContext.className = 'stat-indicator positive';
            } else if (data.avg_engagement_rate > avgThreshold) {
                erContext.textContent = data.platform === 'youtube' ? 'Average View Velocity' : 'Average Engagement';
                erContext.className = 'stat-indicator neutral';
            } else {
                erContext.textContent = data.platform === 'youtube' ? 'Low View Velocity' : 'Low Engagement';
                erContext.className = 'stat-indicator warning';
            }
        } else {
            erContext.textContent = 'N/A';
            erContext.className = 'stat-indicator neutral';
        }

        // 3.1 Detailed Metrics Bindings
        document.getElementById('metric-post-likes').textContent = data.images_avg_likes !== undefined ? formatNumber(data.images_avg_likes) : 'N/A';
        document.getElementById('metric-post-comments').textContent = data.images_avg_comments !== undefined ? formatNumber(data.images_avg_comments) : 'N/A';
        document.getElementById('metric-post-er').textContent = data.followers > 0 ? `${data.images_er}%` : 'N/A';
        
        document.getElementById('metric-reel-likes').textContent = data.reels_avg_likes !== undefined ? formatNumber(data.reels_avg_likes) : 'N/A';
        document.getElementById('metric-reel-comments').textContent = data.reels_avg_comments !== undefined ? formatNumber(data.reels_avg_comments) : 'N/A';
        document.getElementById('metric-reel-views').textContent = data.reels_avg_views !== undefined ? formatNumber(data.reels_avg_views) : 'N/A';
        document.getElementById('metric-reel-er').textContent = data.followers > 0 ? `${data.reels_er}%` : 'N/A';
        document.getElementById('metric-reel-views-ratio').textContent = data.followers > 0 ? `${data.reels_views_to_followers_ratio}%` : 'N/A';

        // Hide cards if all their metrics are 0
        const mediaCard = document.getElementById('media-card-title').closest('.metric-card');
        const hasMediaMetrics = (parseFloat(data.images_avg_likes) > 0) || 
                                (parseFloat(data.images_avg_comments) > 0) || 
                                (parseFloat(data.images_er) > 0);
        mediaCard.style.display = hasMediaMetrics ? 'block' : 'none';

        const videoCard = document.getElementById('video-card-title').closest('.metric-card');
        const hasVideoMetrics = (parseFloat(data.reels_avg_likes) > 0) || 
                                (parseFloat(data.reels_avg_comments) > 0) || 
                                (parseFloat(data.reels_er) > 0) ||
                                (parseFloat(data.reels_avg_views) > 0);
        videoCard.style.display = hasVideoMetrics ? 'block' : 'none';
        


        // 4. Render recent posts list contextually
        postsContainer.innerHTML = '';
        if (!data.recent_posts || data.recent_posts.length === 0) {
            const item = document.createElement('div');
            item.className = 'list-row glass no-posts-message';
            item.style.padding = '24px';
            item.style.justifyContent = 'center';
            item.style.alignItems = 'center';
            item.style.color = 'var(--text-secondary)';
            item.style.fontSize = '0.95rem';
            item.style.fontWeight = '500';
            item.textContent = 'No recent posts retrieved for this public profile.';
            postsContainer.appendChild(item);
        } else {
            data.recent_posts.slice(0, 10).forEach(post => {
                const item = document.createElement('div');
                item.className = 'list-row glass';
                
                const badgeHtml = post.is_sponsored 
                    ? `<span class="post-badge sponsored">Sponsored</span>`
                    : '';
                    
                let rowTypeLabel = '';
                if (data.platform === 'youtube') {
                    rowTypeLabel = post.media_type === 'video' ? '🎥 Video' : '🩳 Short';
                } else if (data.platform === 'twitter') {
                    rowTypeLabel = post.media_type === 'video' ? '🎥 Video' : '🐦 Tweet';
                } else {
                    rowTypeLabel = post.media_type === 'video' ? '🎥 Reel' : '📷 Post';
                }
                
                const likesLabel = 'Likes';
                const commentsLabel = data.platform === 'twitter' ? 'Replies' : 'Comments';
                
                item.innerHTML = `
                    <div class="row-type">
                        ${rowTypeLabel}
                        ${badgeHtml}
                    </div>
                    <div class="row-metrics">
                        ${(data.platform !== 'youtube') ? `
                        <div class="row-metric">
                            <span class="m-label">${likesLabel}</span>
                            <span class="m-value">${formatNumber(post.likes)}</span>
                        </div>
                        ` : ''}
                        ${(post.views > 0 && data.platform !== 'instagram') ? `
                        <div class="row-metric">
                            <span class="m-label">Views</span>
                            <span class="m-value">${formatNumber(post.views)}</span>
                        </div>
                        ` : ''}
                        ${(data.platform === 'youtube') ? '' : `
                        <div class="row-metric">
                            <span class="m-label">${commentsLabel}</span>
                            <span class="m-value">${formatNumber(post.comments)}</span>
                        </div>
                        `}
                        <div class="row-metric highlight">
                            <span class="m-label">ER</span>
                            <span class="m-value">${data.followers > 0 ? post.engagement_rate + '%' : 'N/A'}</span>
                        </div>
                    </div>
                `;
                postsContainer.appendChild(item);
            });
        }
    }
});
