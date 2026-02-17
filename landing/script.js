// GUARDINIA - LANDING PAGE INTERACTIONS

// Smooth scroll para links internos
document.querySelectorAll('a[href^="#"]').forEach(anchor => {
    anchor.addEventListener('click', function (e) {
        e.preventDefault();
        const target = document.querySelector(this.getAttribute('href'));
        if (target) {
            const headerOffset = 80;
            const elementPosition = target.getBoundingClientRect().top;
            const offsetPosition = elementPosition + window.pageYOffset - headerOffset;

            window.scrollTo({
                top: offsetPosition,
                behavior: 'smooth'
            });
        }
    });
});

// Header scroll effect
let lastScroll = 0;
const header = document.querySelector('.header');

window.addEventListener('scroll', () => {
    const currentScroll = window.pageYOffset;

    if (currentScroll <= 0) {
        header.style.boxShadow = '0 2px 10px rgba(30, 58, 138, 0.1)';
        return;
    }

    if (currentScroll > lastScroll && currentScroll > 100) {
        // Scroll down
        header.style.transform = 'translateY(-100%)';
    } else {
        // Scroll up
        header.style.transform = 'translateY(0)';
        header.style.boxShadow = '0 4px 20px rgba(30, 58, 138, 0.15)';
    }

    lastScroll = currentScroll;
});

// Add transition to header
header.style.transition = 'transform 0.3s ease, box-shadow 0.3s ease';

// Animate elements on scroll
const observerOptions = {
    threshold: 0.1,
    rootMargin: '0px 0px -50px 0px'
};

const observer = new IntersectionObserver((entries) => {
    entries.forEach(entry => {
        if (entry.isIntersecting) {
            entry.target.style.opacity = '1';
            entry.target.style.transform = 'translateY(0)';
        }
    });
}, observerOptions);

// Observe all cards and sections
document.querySelectorAll('.stat-card, .tech-card, .category-card, .step').forEach(el => {
    el.style.opacity = '0';
    el.style.transform = 'translateY(30px)';
    el.style.transition = 'opacity 0.6s ease, transform 0.6s ease';
    observer.observe(el);
});

// Track button clicks (optional analytics)
document.querySelectorAll('.btn').forEach(button => {
    button.addEventListener('click', () => {
        const buttonText = button.textContent.trim();
        console.log('Button clicked:', buttonText);
        // Aqui você pode adicionar Google Analytics ou outro tracking
        // gtag('event', 'button_click', { button_name: buttonText });
    });
});

// Add loading animation to external links
document.querySelectorAll('a[href^="http"]').forEach(link => {
    link.addEventListener('click', function(e) {
        if (!this.hasAttribute('target')) {
            this.style.opacity = '0.6';
        }
    });
});

console.log('🛡️ GuardinIA Landing Page loaded successfully!');
