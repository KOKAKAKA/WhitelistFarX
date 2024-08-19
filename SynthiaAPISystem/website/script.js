document.querySelectorAll('.tab-button').forEach(button => {
    button.addEventListener('click', function() {
        document.querySelectorAll('.tab-button').forEach(btn => btn.classList.remove('active'));
        document.querySelectorAll('.tab-content').forEach(section => {
            section.classList.remove('active', 'appear');
            section.classList.add('disappear');
        });
        const target = document.querySelector(this.getAttribute('href'));
        target.classList.remove('disappear');
        target.classList.add('appear', 'active');
        this.classList.add('active');
    });
});

function closeSection(button) {
    button.parentElement.classList.remove('active');
    button.parentElement.classList.add('disappear');
}
