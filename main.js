document.addEventListener('DOMContentLoaded', () => {
    let currentProfileData = null;
    const searchForm = document.getElementById('search-form');
    const handleInput = document.getElementById('handle-input');
    const searchBtn = document.getElementById('search-btn');
    const btnText = searchBtn.querySelector('.btn-text');
    const btnLoader = searchBtn.querySelector('.btn-loader');
    
    // Adjust Stats Elements
    const adjustStatsBtn = document.getElementById('adjust-stats-btn');
    const adjustStatsPanel = document.getElementById('adjust-stats-panel');
    const adjFollowersInput = document.getElementById('adj-followers');
    const adjFollowingInput = document.getElementById('adj-following');
    const adjCancelBtn = document.getElementById('adj-cancel-btn');
    const adjSaveBtn = document.getElementById('adj-save-btn');
    
    const errorContainer = document.getElementById('error-container');
    const dashboard = document.getElementById('dashboard');
    
    // Profile Header Elements
    const profileHandle = document.getElementById('profile-handle');
    const profileName = document.getElementById('profile-name');
    const profileBio = document.getElementById('profile-bio');
    const profileTopics = document.getElementById('profile-topics');
    const profileLink = document.getElementById('profile-link');
    const profileSource = document.getElementById('profile-source');
    
    // Stats Elements
    const statFollowers = document.getElementById('stat-followers');
    const statReach = document.getElementById('stat-reach');
    const statScore = document.getElementById('stat-score');
    const statER = document.getElementById('stat-er');
    const erContext = document.getElementById('er-context');
    

    
    // Container Elements
    const postsContainer = document.getElementById('posts-container');
    


    // API Base URL (FastAPI)
    const API_BASE = 'http://localhost:8000/api';



    // Preset Suggestions Buttons
    const tagBtns = document.querySelectorAll('.tag-btn');
    tagBtns.forEach(btn => {
        btn.addEventListener('click', () => {
            const handle = btn.getAttribute('data-handle');
            handleInput.value = handle;
            triggerSearch(handle);
        });
    });

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
            const res = await fetch(`${API_BASE}/analyze/${encodeURIComponent(handle)}`);
            if (!res.ok) {
                const errData = await res.json();
                throw new Error(errData.detail || 'Failed to fetch profile analysis.');
            }
            
            const data = await res.json();
            renderDashboard(data);
        } catch (err) {
            console.error(err);
            showError(err.message || 'Server error. Make sure backend is running on port 8000.');
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

    function renderDashboard(data) {
        currentProfileData = data;
        
        // Show Dashboard Container
        dashboard.classList.remove('hidden');
        adjustStatsBtn.classList.remove('hidden');
        
        // 1. Profile Header
        profileHandle.textContent = `@${data.handle}`;
        profileName.textContent = data.full_name;
        profileBio.textContent = data.biography;
        profileLink.href = `https://instagram.com/${data.handle}`;
        
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
        
        // Topics tags are removed as requested by user
        profileTopics.innerHTML = '';

        // 2. Stats Cards
        statFollowers.textContent = data.followers > 0 ? formatNumber(data.followers) : 'N/A';
        statER.textContent = data.followers > 0 ? `${data.avg_engagement_rate}%` : 'N/A';
        

        
        // Quality Contexts
        if (data.followers > 0) {
            if (data.avg_engagement_rate > 4.0) {
                erContext.textContent = 'High Engagement';
                erContext.className = 'stat-indicator positive';
            } else if (data.avg_engagement_rate > 2.0) {
                erContext.textContent = 'Average Engagement';
                erContext.className = 'stat-indicator neutral';
            } else {
                erContext.textContent = 'Low Engagement';
                erContext.className = 'stat-indicator warning';
            }
        } else {
            erContext.textContent = 'N/A';
            erContext.className = 'stat-indicator neutral';
        }

        // 2.1 Detailed Metrics Bindings
        document.getElementById('metric-post-likes').textContent = data.followers > 0 ? formatNumber(data.images_avg_likes) : 'N/A';
        document.getElementById('metric-post-comments').textContent = data.followers > 0 ? formatNumber(data.images_avg_comments) : 'N/A';
        document.getElementById('metric-post-er').textContent = data.followers > 0 ? `${data.images_er}%` : 'N/A';
        
        document.getElementById('metric-reel-likes').textContent = data.followers > 0 ? formatNumber(data.reels_avg_likes) : 'N/A';
        document.getElementById('metric-reel-comments').textContent = data.followers > 0 ? formatNumber(data.reels_avg_comments) : 'N/A';
        document.getElementById('metric-reel-er').textContent = data.followers > 0 ? `${data.reels_er}%` : 'N/A';
        document.getElementById('metric-reel-views-ratio').textContent = data.followers > 0 ? `${data.reels_views_to_followers_ratio}%` : 'N/A';
        
        document.getElementById('metric-likes-comments-ratio').textContent = data.followers > 0 ? data.likes_to_comments_ratio : 'N/A';




        // 3. Render recent posts list
        postsContainer.innerHTML = '';
        data.recent_posts.slice(0, 10).forEach(post => {
            const item = document.createElement('div');
            item.className = 'list-row glass';
            
            const badgeHtml = post.is_sponsored 
                ? `<span class="post-badge sponsored">Sponsored</span>`
                : '';
            
            item.innerHTML = `
                <div class="row-type">
                    ${post.media_type === 'video' ? '🎥 Reel' : '📷 Post'}
                    ${badgeHtml}
                </div>
                <div class="row-metrics">
                    ${post.views > 0 ? `
                    <div class="row-metric">
                        <span class="m-label">Views</span>
                        <span class="m-value">${formatNumber(post.views)}</span>
                    </div>
                    ` : `
                    <div class="row-metric">
                        <span class="m-label">Likes</span>
                        <span class="m-value">${formatNumber(post.likes)}</span>
                    </div>
                    `}
                    <div class="row-metric">
                        <span class="m-label">Comments</span>
                        <span class="m-value">${formatNumber(post.comments)}</span>
                    </div>
                    <div class="row-metric highlight">
                        <span class="m-label">ER</span>
                        <span class="m-value">${post.views > 0 ? 'N/A' : (data.followers > 0 ? post.engagement_rate + '%' : 'N/A')}</span>
                    </div>
                </div>
            `;
            postsContainer.appendChild(item);
        });


    }



    // Overrides click logic
    adjustStatsBtn.addEventListener('click', () => {
        if (currentProfileData) {
            adjFollowersInput.value = currentProfileData.followers;
            adjFollowingInput.value = currentProfileData.following || 0;
            adjustStatsPanel.classList.toggle('hidden');
        }
    });
    
    adjCancelBtn.addEventListener('click', () => {
        adjustStatsPanel.classList.add('hidden');
    });
    
    adjSaveBtn.addEventListener('click', () => {
        if (!currentProfileData) return;
        
        const rawFollowers = adjFollowersInput.value.trim();
        const rawFollowing = adjFollowingInput.value.trim();
        
        const newFollowers = parseInt(rawFollowers.replace(/,/g, ''), 10);
        const newFollowing = parseInt(rawFollowing.replace(/,/g, ''), 10);
        
        if (isNaN(newFollowers) || newFollowers <= 0) {
            alert('Please enter a valid positive number for Followers.');
            return;
        }
        
        currentProfileData.followers = newFollowers;
        currentProfileData.following = isNaN(newFollowing) ? 0 : newFollowing;
        
        // Recalculate engagement rates
        let totalER = 0;
        currentProfileData.recent_posts.forEach(post => {
            post.engagement_rate = parseFloat((((post.likes + post.comments) / newFollowers) * 100).toFixed(2));
            totalER += post.engagement_rate;
        });
        
        currentProfileData.avg_engagement_rate = parseFloat((totalER / Math.max(currentProfileData.recent_posts.length, 1)).toFixed(2));
        
        // Recalculate estimated reach
        let reach = Math.round(newFollowers * (currentProfileData.avg_engagement_rate / 100) * 2.5);
        reach = Math.min(reach, newFollowers);
        reach = Math.max(reach, Math.round(newFollowers * 0.05));
        currentProfileData.estimated_reach = reach;
        
        // Recalculate influence score
        const score = Math.min(Math.max((newFollowers ** 0.15) * (currentProfileData.avg_engagement_rate ** 0.4), 1.0), 10.0);
        currentProfileData.influence_score = parseFloat(score.toFixed(1));
        
        // Recalculate Images vs Reels stats
        const imagesLikes = currentProfileData.recent_posts.filter(p => p.media_type === 'image').map(p => p.likes);
        const imagesComments = currentProfileData.recent_posts.filter(p => p.media_type === 'image').map(p => p.comments);
        const reelsLikes = currentProfileData.recent_posts.filter(p => p.media_type !== 'image').map(p => p.likes);
        const reelsComments = currentProfileData.recent_posts.filter(p => p.media_type !== 'image').map(p => p.comments);
        const reelsViews = currentProfileData.recent_posts.filter(p => p.media_type !== 'image' && p.views > 0).map(p => p.views);
        
        const imgAvgLikes = imagesLikes.length ? (imagesLikes.reduce((a,b) => a+b, 0) / imagesLikes.length) : 0;
        const imgAvgComments = imagesComments.length ? (imagesComments.reduce((a,b) => a+b, 0) / imagesComments.length) : 0;
        currentProfileData.images_avg_likes = parseFloat(imgAvgLikes.toFixed(1));
        currentProfileData.images_avg_comments = parseFloat(imgAvgComments.toFixed(1));
        currentProfileData.images_er = parseFloat((((imgAvgLikes + imgAvgComments) / newFollowers) * 100).toFixed(2));
        
        const reelsAvgLikes = reelsLikes.length ? (reelsLikes.reduce((a,b) => a+b, 0) / reelsLikes.length) : 0;
        const reelsAvgComments = reelsComments.length ? (reelsComments.reduce((a,b) => a+b, 0) / reelsComments.length) : 0;
        currentProfileData.reels_avg_likes = parseFloat(reelsAvgLikes.toFixed(1));
        currentProfileData.reels_avg_comments = parseFloat(reelsAvgComments.toFixed(1));
        currentProfileData.reels_er = parseFloat((((reelsAvgLikes + reelsAvgComments) / newFollowers) * 100).toFixed(2));

        const reelsAvgViews = reelsViews.length ? (reelsViews.reduce((a,b) => a+b, 0) / reelsViews.length) : 0;
        currentProfileData.reels_views_to_followers_ratio = parseFloat((((reelsAvgViews) / newFollowers) * 100).toFixed(2));

        const totalLikes = currentProfileData.recent_posts.reduce((acc, p) => acc + p.likes, 0);
        const totalComments = currentProfileData.recent_posts.reduce((acc, p) => acc + p.comments, 0);
        currentProfileData.likes_to_comments_ratio = parseFloat((totalLikes / Math.max(totalComments, 1)).toFixed(2));
        
        renderDashboard(currentProfileData);
        adjustStatsPanel.classList.add('hidden');
    });
});
