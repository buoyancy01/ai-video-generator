document.addEventListener('DOMContentLoaded', function() {
    // Handle background type selection
    const bgTypeRadios = document.querySelectorAll('input[name="bg-type"]');
    bgTypeRadios.forEach(radio => {
        radio.addEventListener('change', function() {
            const bgImageUpload = document.getElementById('bg-image-upload');
            const bgColorSelect = document.getElementById('bg-color-select');
            if (this.value === 'image') {
                bgImageUpload.style.display = 'block';
                bgColorSelect.style.display = 'none';
            } else {
                bgImageUpload.style.display = 'none';
                bgColorSelect.style.display = 'block';
            }
        });
    });

    // Handle drag and drop for product image
    const dropArea = document.getElementById('drop-area');
    const productImageInput = document.getElementById('product_image');
    const productPreview = document.getElementById('product-preview');
    
    dropArea.addEventListener('click', function() {
        productImageInput.click();
    });
    
    productImageInput.addEventListener('change', function() {
        if (this.files && this.files[0]) {
            const reader = new FileReader();
            reader.onload = function(e) {
                productPreview.src = e.target.result;
                productPreview.style.display = 'block';
            };
            reader.readAsDataURL(this.files[0]);
        }
    });
    
    dropArea.addEventListener('dragover', function(e) {
        e.preventDefault();
        this.style.borderColor = '#6a11cb';
        this.style.backgroundColor = 'rgba(106, 17, 203, 0.1)';
    });
    
    dropArea.addEventListener('dragleave', function() {
        this.style.borderColor = '#e2e8f0';
        this.style.backgroundColor = 'rgba(106, 17, 203, 0.03)';
    });
    
    dropArea.addEventListener('drop', function(e) {
        e.preventDefault();
        this.style.borderColor = '#e2e8f0';
        this.style.backgroundColor = 'rgba(106, 17, 203, 0.03)';
        
        const file = e.dataTransfer.files[0];
        if (file && ['image/png', 'image/jpeg'].includes(file.type)) {
            productImageInput.files = e.dataTransfer.files;
            const reader = new FileReader();
            reader.onload = function(e) {
                productPreview.src = e.target.result;
                productPreview.style.display = 'block';
            };
            reader.readAsDataURL(file);
        }
    });

    // Background image preview
    const bgImageInput = document.getElementById('background_image');
    const bgPreview = document.getElementById('bg-preview');
    
    bgImageInput.addEventListener('change', function() {
        if (this.files && this.files[0]) {
            const reader = new FileReader();
            reader.onload = function(e) {
                bgPreview.src = e.target.result;
                bgPreview.style.display = 'block';
            };
            reader.readAsDataURL(this.files[0]);
        }
    });

    // Background color preview
    const bgColorInput = document.getElementById('background_color');
    const colorPreview = document.getElementById('color-preview');
    const colorValue = document.getElementById('color-value');
    
    bgColorInput.addEventListener('input', function() {
        colorPreview.style.backgroundColor = this.value;
        colorValue.textContent = this.value;
    });

    // Character counter for textarea
    const scriptTextarea = document.getElementById('script');
    const charCount = document.getElementById('char-count');
    
    scriptTextarea.addEventListener('input', function() {
        charCount.textContent = this.value.length;
    });

    // Show loading spinner on form submit
    document.getElementById('video-form').addEventListener('submit', function() {
        document.getElementById('loading').style.display = 'flex';
        document.getElementById('video-preview').style.display = 'none';
    });
});
