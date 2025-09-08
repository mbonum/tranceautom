document.addEventListener('DOMContentLoaded', function () {
    const table = document.getElementById('products-table');
    if (!table) return;

    const headers = table.querySelectorAll('th');

    headers.forEach(header => {
        // Don't add a handle to the very last column
        if (header.nextElementSibling) {
            const resizeHandle = document.createElement('div');
            resizeHandle.className = 'resize-handle';
            header.appendChild(resizeHandle);

            makeResizable(header, resizeHandle);
        }
    });

    function makeResizable(header, handle) {
        let x = 0;
        let w = 0;

        const mouseDownHandler = function (e) {
            // Prevent text selection
            e.preventDefault();

            x = e.clientX;
            const styles = window.getComputedStyle(header);
            w = parseInt(styles.width, 10);

            document.addEventListener('mousemove', mouseMoveHandler);
            document.addEventListener('mouseup', mouseUpHandler);
            handle.classList.add('resizing');
        };

        const mouseMoveHandler = function (e) {
            const dx = e.clientX - x;
            const newWidth = w + dx;
            if (newWidth > 50) { // Set a minimum width
                header.style.width = `${newWidth}px`;
                // For performance, you might want to adjust table layout properties here
                // For simplicity, we're just setting the header width.
                // Modern browsers often adjust the column automatically.
            }
        };

        const mouseUpHandler = function () {
            document.removeEventListener('mousemove', mouseMoveHandler);
            document.removeEventListener('mouseup', mouseUpHandler);
            handle.classList.remove('resizing');
        };

        handle.addEventListener('mousedown', mouseDownHandler);
    }
});