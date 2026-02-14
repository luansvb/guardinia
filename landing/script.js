// ===================================
// GUARDINIA - MAIN JAVASCRIPT
// ===================================

// Wait for DOM to be ready
document.addEventListener('DOMContentLoaded', function() {
    
    // ===================================
    // PARTICLES.JS CONFIGURATION
    // ===================================
    
    if (typeof particlesJS !== 'undefined') {
        particlesJS('particles-js', {
            particles: {
                number: {
                    value: 80,
                    density: {
                        enable: true,
                        value_area: 800
                    }
                },
                color: {
                    value: '#3b82f6'
                },
                shape: {
                    type: 'circle',
                    stroke: {
                        width: 0,
                        color: '#000000'
                    }
                },
                opacity: {
                    value: 0.3,
                    random: true,
                    anim: {
                        enable: true,
                        speed: 1,
                        opacity_min: 0.1,
                        sync: false
                    }
                },
                size: {
                    value: 3,
                    random: true,
                    anim: {
                        enable: true,
                        speed: 2,
                        size_min: 0.1,
                        sync: false
                    }
                },
                line_linked: {
                    enable: true,
                    distance: 150,
                    color: '#3b82f6',
                    opacity: 0.2,
                    width: 1
                },
                move: {
                    enable: true,
                    speed: 2,
                    direction: 'none',
                    random: false,
                    straight: false,
                    out_mode: 'out',
                    bounce: false,
                    attract: {
                        enable: false,
                        rotateX: 600,
                        rotateY: 1200
                    }
                }
            },
            interactivity: {
                detect_on: 'canvas',
                events: {
                    onhover: {
                        enable: true,
                        mode: 'grab'
                    },
                    onclick: {
                        enable: true,
                        mode: 'push'
                    },
                    resize: true
                },
                modes: {
                    grab: {
                        distance: 140,
                        line_linked: {
                            opacity: 0.5
                        }
                    },
                    push: {
                        particles_nb: 4
                    }
                }
            },
            retina_detect: true
        });
    }
    
    // ===================================
    // NAVBAR SCROLL EFFECT
    // ===================================
    
    const navbar = document.querySelector('.navbar');
    
    window.addEventListener('scroll', function() {
        if (window.scrollY > 50) {
            navbar.classList.add('scrolled');
        } else {
            navbar.classList.remove('scrolled');
        }
    });
    
    // ===================================
    // SMOOTH SCROLL FOR NAVIGATION LINKS
    // ===================================
    
    document.querySelectorAll('a[href^="#"]').forEach(anchor => {
        anchor.addEventListener('click', function(e) {
            const href = this.getAttribute('href');
            
            // Don't prevent default for empty hash or just #
            if (href === '#' || href === '') {
                return;
            }
            
            const target = document.querySelector(href);
            
            if (target) {
                e.preventDefault();
                
                const navbarHeight = navbar.offsetHeight;
                const targetPosition = target.getBoundingClientRect().top + window.pageYOffset - navbarHeight;
                
                window.scrollTo({
                    top: targetPosition,
                    behavior: 'smooth'
                });
                
                // Close mobile menu if open
                const navLinks = document.querySelector('.nav-links');
                if (navLinks.classList.contains('active')) {
                    navLinks.classList.remove('active');
                    hamburger.classList.remove('active');
                }
            }
        });
    });
    
    // ===================================
    // MOBILE HAMBURGER MENU
    // ===================================
    
    const hamburger = document.getElementById('hamburger');
    const navLinks = document.querySelector('.nav-links');
    
    if (hamburger) {
        hamburger.addEventListener('click', function() {
            hamburger.classList.toggle('active');
            navLinks.classList.toggle('active');
            
            // Animate hamburger icon
            const spans = hamburger.querySelectorAll('span');
            if (hamburger.classList.contains('active')) {
                spans[0].style.transform = 'rotate(45deg) translate(5px, 5px)';
                spans[1].style.opacity = '0';
                spans[2].style.transform = 'rotate(-45deg) translate(7px, -6px)';
            } else {
                spans[0].style.transform = 'none';
                spans[1].style.opacity = '1';
                spans[2].style.transform = 'none';
            }
        });
    }
    
    // Close mobile menu when clicking outside
    document.addEventListener('click', function(event) {
        if (navLinks && navLinks.classList.contains('active')) {
            const isClickInsideNav = navLinks.contains(event.target);
            const isClickOnHamburger = hamburger.contains(event.target);
            
            if (!isClickInsideNav && !isClickOnHamburger) {
                navLinks.classList.remove('active');
                hamburger.classList.remove('active');
                
                const spans = hamburger.querySelectorAll('span');
                spans[0].style.transform = 'none';
                spans[1].style.opacity = '1';
                spans[2].style.transform = 'none';
            }
        }
    });
    
    // ===================================
    // INTERSECTION OBSERVER FOR ANIMATIONS
    // ===================================
    
    const observerOptions = {
        threshold: 0.1,
        rootMargin: '0px 0px -100px 0px'
    };
    
    const observer = new IntersectionObserver(function(entries) {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                entry.target.classList.add('fade-in-up');
                observer.unobserve(entry.target);
            }
        });
    }, observerOptions);
    
    // Observe all feature cards
    document.querySelectorAll('.feature-card').forEach(card => {
        observer.observe(card);
    });
    
    // Observe all category cards
    document.querySelectorAll('.category-card').forEach(card => {
        observer.observe(card);
    });
    
    // Observe all security items
    document.querySelectorAll('.security-item').forEach(item => {
        observer.observe(item);
    });
    
    // Observe demo cards
    document.querySelectorAll('.demo-card').forEach(card => {
        observer.observe(card);
    });
    
    // ===================================
    // ANIMATED COUNTERS
    // ===================================
    
    function animateCounter(element, target, duration = 2000) {
        const start = 0;
        const increment = target / (duration / 16); // 60 FPS
        let current = start;
        
        const timer = setInterval(function() {
            current += increment;
            if (current >= target) {
                element.textContent = target;
                clearInterval(timer);
            } else {
                element.textContent = Math.floor(current);
            }
        }, 16);
    }
    
    // Counter observer
    const counterObserver = new IntersectionObserver(function(entries) {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                const counter = entry.target;
                const target = parseInt(counter.getAttribute('data-target'));
                
                if (!counter.classList.contains('counted')) {
                    animateCounter(counter, target);
                    counter.classList.add('counted');
                }
                
                counterObserver.unobserve(counter);
            }
        });
    }, { threshold: 0.5 });
    
    document.querySelectorAll('.counter').forEach(counter => {
        counterObserver.observe(counter);
    });
    
    // ===================================
    // PARALLAX EFFECT FOR HERO
    // ===================================
    
    window.addEventListener('scroll', function() {
        const scrolled = window.pageYOffset;
        const heroVisual = document.querySelector('.hero-visual');
        
        if (heroVisual && scrolled < window.innerHeight) {
            heroVisual.style.transform = `translateY(${scrolled * 0.5}px)`;
        }
    });
    
    // ===================================
    // DYNAMIC YEAR IN FOOTER
    // ===================================
    
    const yearElements = document.querySelectorAll('.current-year');
    const currentYear = new Date().getFullYear();
    yearElements.forEach(element => {
        element.textContent = currentYear;
    });
    
    // ===================================
    // FEATURE CARD HOVER EFFECTS
    // ===================================
    
    document.querySelectorAll('.feature-card').forEach(card => {
        card.addEventListener('mouseenter', function() {
            this.style.transform = 'translateY(-5px) scale(1.02)';
        });
        
        card.addEventListener('mouseleave', function() {
            this.style.transform = 'translateY(0) scale(1)';
        });
    });
    
    // ===================================
    // TYPING EFFECT FOR HERO SUBTITLE (Optional)
    // ===================================
    
    function typeWriter(element, text, speed = 50) {
        let i = 0;
        element.textContent = '';
        
        function type() {
            if (i < text.length) {
                element.textContent += text.charAt(i);
                i++;
                setTimeout(type, speed);
            }
        }
        
        type();
    }
    
    // Uncomment to enable typing effect
    // const heroSubtitle = document.querySelector('.hero-subtitle');
    // if (heroSubtitle) {
    //     const originalText = heroSubtitle.textContent;
    //     typeWriter(heroSubtitle, originalText, 30);
    // }
    
    // ===================================
    // SCROLL TO TOP BUTTON (Optional Enhancement)
    // ===================================
    
    function createScrollToTopButton() {
        const button = document.createElement('button');
        button.innerHTML = '<i class="fas fa-arrow-up"></i>';
        button.className = 'scroll-to-top';
        button.style.cssText = `
            position: fixed;
            bottom: 30px;
            right: 30px;
            width: 50px;
            height: 50px;
            border-radius: 50%;
            background: linear-gradient(135deg, #3b82f6 0%, #06b6d4 100%);
            color: white;
            border: none;
            cursor: pointer;
            display: none;
            align-items: center;
            justify-content: center;
            font-size: 1.2rem;
            box-shadow: 0 4px 15px rgba(59, 130, 246, 0.4);
            transition: all 0.3s ease;
            z-index: 999;
        `;
        
        button.addEventListener('click', function() {
            window.scrollTo({
                top: 0,
                behavior: 'smooth'
            });
        });
        
        button.addEventListener('mouseenter', function() {
            this.style.transform = 'translateY(-5px)';
            this.style.boxShadow = '0 6px 20px rgba(59, 130, 246, 0.6)';
        });
        
        button.addEventListener('mouseleave', function() {
            this.style.transform = 'translateY(0)';
            this.style.boxShadow = '0 4px 15px rgba(59, 130, 246, 0.4)';
        });
        
        window.addEventListener('scroll', function() {
            if (window.pageYOffset > 300) {
                button.style.display = 'flex';
            } else {
                button.style.display = 'none';
            }
        });
        
        document.body.appendChild(button);
    }
    
    createScrollToTopButton();
    
    // ===================================
    // PERFORMANCE OPTIMIZATION
    // ===================================
    
    // Lazy load images
    if ('IntersectionObserver' in window) {
        const imageObserver = new IntersectionObserver((entries, observer) => {
            entries.forEach(entry => {
                if (entry.isIntersecting) {
                    const img = entry.target;
                    img.src = img.dataset.src;
                    img.classList.remove('lazy');
                    observer.unobserve(img);
                }
            });
        });
        
        document.querySelectorAll('img.lazy').forEach(img => {
            imageObserver.observe(img);
        });
    }
    
    // ===================================
    // CONSOLE MESSAGE
    // ===================================
    
    console.log('%c GuardinIA ', 
        'background: linear-gradient(135deg, #3b82f6 0%, #06b6d4 100%); color: white; font-size: 20px; font-weight: bold; padding: 10px;');
    console.log('%c Sistema Inteligente de Detecção de Golpes ', 
        'color: #3b82f6; font-size: 14px; font-weight: bold;');
    console.log('%c Desenvolvido com 💙 ', 
        'color: #06b6d4; font-size: 12px;');
    
    // ===================================
    // ANALYTICS & TRACKING (Optional)
    // ===================================
    
    // Track button clicks
    document.querySelectorAll('a[href*="whatsapp"], a[href*="github"]').forEach(link => {
        link.addEventListener('click', function() {
            const action = this.href.includes('whatsapp') ? 'whatsapp_click' : 'github_click';
            console.log('Event tracked:', action);
            // Add your analytics code here (Google Analytics, etc.)
        });
    });
    
    // ===================================
    // ACCESSIBILITY IMPROVEMENTS
    // ===================================
    
    // Add keyboard navigation
    document.querySelectorAll('.feature-card, .category-card, .demo-card').forEach(card => {
        card.setAttribute('tabindex', '0');
        
        card.addEventListener('keypress', function(e) {
            if (e.key === 'Enter' || e.key === ' ') {
                const link = this.querySelector('a');
                if (link) {
                    link.click();
                }
            }
        });
    });
    
    // ===================================
    // MOBILE RESPONSIVE ADJUSTMENTS
    // ===================================
    
    function handleMobileMenu() {
        if (window.innerWidth <= 768) {
            // Add mobile-specific styles
            navLinks.style.position = 'fixed';
            navLinks.style.top = '70px';
            navLinks.style.right = '-100%';
            navLinks.style.width = '100%';
            navLinks.style.height = 'calc(100vh - 70px)';
            navLinks.style.backgroundColor = 'rgba(15, 23, 41, 0.98)';
            navLinks.style.flexDirection = 'column';
            navLinks.style.justifyContent = 'flex-start';
            navLinks.style.padding = '2rem';
            navLinks.style.transition = 'right 0.3s ease';
            
            if (navLinks.classList.contains('active')) {
                navLinks.style.right = '0';
            }
        } else {
            // Reset styles for desktop
            navLinks.style.position = 'static';
            navLinks.style.flexDirection = 'row';
            navLinks.style.height = 'auto';
            navLinks.style.width = 'auto';
            navLinks.style.backgroundColor = 'transparent';
            navLinks.style.padding = '0';
        }
    }
    
    window.addEventListener('resize', handleMobileMenu);
    handleMobileMenu(); // Call on load
    
    // ===================================
    // LOADING ANIMATION
    // ===================================
    
    window.addEventListener('load', function() {
        document.body.classList.add('loaded');
        
        // Fade in sections
        setTimeout(function() {
            document.querySelectorAll('section').forEach((section, index) => {
                setTimeout(function() {
                    section.style.opacity = '1';
                    section.style.transform = 'translateY(0)';
                }, index * 100);
            });
        }, 300);
    });
    
    // Initialize section styles
    document.querySelectorAll('section').forEach(section => {
        section.style.opacity = '0';
        section.style.transform = 'translateY(20px)';
        section.style.transition = 'opacity 0.6s ease, transform 0.6s ease';
    });
    
});

// ===================================
// EXTERNAL CLICK HANDLING
// ===================================

// Handle external links
document.addEventListener('click', function(e) {
    const link = e.target.closest('a');
    if (link && link.hostname !== window.location.hostname) {
        // Could add analytics or confirmation for external links
        console.log('External link clicked:', link.href);
    }
});

// ===================================
// ERROR HANDLING
// ===================================

window.addEventListener('error', function(e) {
    console.error('JavaScript error:', e.message);
    // Could send error to analytics or logging service
});

// ===================================
// SERVICE WORKER REGISTRATION (Optional)
// ===================================

if ('serviceWorker' in navigator) {
    // Uncomment to enable service worker
    // window.addEventListener('load', function() {
    //     navigator.serviceWorker.register('/sw.js')
    //         .then(reg => console.log('Service Worker registered'))
    //         .catch(err => console.log('Service Worker registration failed'));
    // });
}
