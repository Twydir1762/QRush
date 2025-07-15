function createCloud() {
    const sky = document.getElementById('sky');
    const cloud = document.createElement('div');
    cloud.className = 'cloud';

    // Размер и позиция облака
    const width = Math.random() * 180 + 220;
    const height = width * (0.4 + Math.random() * 0.25);
    const top = Math.random() * 60;
    const duration = Math.random() * 30 + 40;
    const opacity = 0.85 + Math.random() * 0.1;

    cloud.style.width = `${width}px`;
    cloud.style.height = `${height}px`;
    cloud.style.top = `${top}%`;

    cloud.style.left = `105vw`;
    cloud.style.opacity = opacity;
    cloud.style.animationDuration = `${duration}s`;

    const bubbles = 8 + Math.floor(Math.random() * 8);
    for (let j = 0; j < bubbles; j++) {
        const bubble = document.createElement('div');
        bubble.className = 'cloud-bubble';

        const bWidth = width * (0.18 + Math.random() * 0.35);
        const bHeight = bWidth * (0.7 + Math.random() * 0.7);
        bubble.style.width = `${bWidth}px`;
        bubble.style.height = `${bHeight}px`;

        bubble.style.left = `${Math.random() * (width - bWidth * 0.7)}px`;
        bubble.style.top = `${Math.random() * (height - bHeight * 0.7)}px`;
        bubble.style.opacity = 0.5 + Math.random() * 0.35;

        cloud.appendChild(bubble);
    }

    cloud.addEventListener('animationend', () => {
        cloud.remove();
        setTimeout(createCloud, Math.random() * 2000);
    });

    sky.appendChild(cloud);
}

window.onload = function() {
    for (let i = 0; i < 16; i++) {
        setTimeout(createCloud, i * 4000 + Math.random() * 2000);
    }
};