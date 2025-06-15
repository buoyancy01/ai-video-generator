document.addEventListener('DOMContentLoaded', function() {
    // Handle background type selection
    const bgTypeRadios = document.querySelectorAll('input[name="bg-type"]');
    bgTypeRadios.forEach(radio => {
        radio.addEventListener('change', function() {
            if (this.value === 'image') {
                document.getElementById('bg-image-upload').style.display = 'block';
                document.getElementById('bg-color-select').style.display = 'none';
            } else {
                document.getElementById('bg-image-upload').style.display = 'none';
                document.getElementById('bg-color-select').style.display = 'block';
            }
        });
    });

    // Handle drag and drop for product image
    const dropArea = document.getElementById('drop-area');
    dropArea.addEventListener('click', function() {
        document.getElementById('product_image').click();
    });
    dropArea.addEventListener('dragover', function(e) {
        e.preventDefault();
        this.style.borderColor = '#3498db';
    });
    dropArea.addEventListener('dragleave', function() {
        this.style.borderColor = '#ccc';
    });
    dropArea.addEventListener('drop', function(e) {
        e.preventDefault();
        this.style.borderColor = '#ccc';
        const file = e.dataTransfer.files[0];
        if (file && ['image/png', 'image/jpeg'].includes(file.type)) {
            document.getElementById('product_image').files = e.dataTransfer.files;
            // Optionally, display the file name or a preview
        }
    });

    // Show loading spinner on form submit
    document.querySelector('form').addEventListener('submit', function() {
        document.getElementById('loading').style.display = 'block';
    });
});
