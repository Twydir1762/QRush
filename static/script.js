document.addEventListener('DOMContentLoaded', () => {
    const uploadForm = document.getElementById('uploadForm');
    const fileInput = document.getElementById('fileInput');
    const hoursInput = document.getElementById('hoursInput');
    const uploadButton = document.getElementById('uploadButton');
    const buttonText = uploadButton.querySelector('.button-text');
    const spinner = uploadButton.querySelector('.spinner');
    const messageArea = document.getElementById('messageArea');
    const fileNameDisplay = document.getElementById('fileName');
    const resultDiv = document.getElementById('result');
    const downloadLink = document.getElementById('download-link');
    const qrImage = document.getElementById('qr-image');

    fileInput.addEventListener('change', () => {
        if (fileInput.files.length > 0) {
            fileNameDisplay.textContent = fileInput.files[0].name;
            fileNameDisplay.title = fileInput.files[0].name; // For long names
        } else {
            fileNameDisplay.textContent = 'Файл не выбран';
        }
    });

    uploadForm.addEventListener('submit', async (event) => {
        event.preventDefault();

        const file = fileInput.files[0];
        const hours = parseInt(hoursInput.value, 10);

        messageArea.textContent = '';
        messageArea.className = 'message-area'; // Reset classes

        if (!file) {
            showMessage('Пожалуйста, выберите файл.', 'error');
            return;
        }

        if (isNaN(hours) || hours < 1 || hours > 24) {
            showMessage('Пожалуйста, укажите срок хранения от 1 до 24 часов.', 'error');
            return;
        }

        // Start loading spinner
        buttonText.style.display = 'none';
        spinner.style.display = 'inline-block';
        uploadButton.disabled = true;

        try {
            const formData = new FormData();
            formData.append('uploaded_file', file);
            formData.append('avail_period', hours);

            // Make the POST request to upload the file
            const response = await fetch('/upload', {
                method: 'POST',
                body: formData
            });

            if (!response.ok) {
                throw new Error('Ошибка при загрузке файла');
            }

            const data = await response.json();

            // Display success message
            showMessage(`Файл "${file.name}" (${formatFileSize(file.size)}) успешно загружен.`, 'success');

            const downloadUrl = `${window.location.origin}${data.download_link}`;
            const qrCodeUrl = data.qr_code;

            downloadLink.href = downloadUrl;
            downloadLink.textContent = downloadUrl;

            const qrBlob = await fetch(qrCodeUrl).then(res => res.blob());
            qrImage.src = URL.createObjectURL(qrBlob);

            // Показываем результат
            resultDiv.style.display = 'block';
            // Скрываем форму загрузки
            uploadForm.style.display = 'none';
        } catch (error) {
            showMessage('Ошибка сети или сервера.', 'error');
            console.error(error);
        } finally {
            buttonText.style.display = 'inline-block';
            spinner.style.display = 'none';
            uploadButton.disabled = false;
        }
    });

    function showMessage(message, type) {
        messageArea.textContent = message;
        messageArea.className = `message-area ${type}`; // type can be 'success' or 'error'
    }

    function formatFileSize(bytes, decimals = 2) {
        if (bytes === 0) return '0 Bytes';
        const k = 1024;
        const dm = decimals < 0 ? 0 : decimals;
        const sizes = ['Bytes', 'KB', 'MB', 'GB', 'TB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        return parseFloat((bytes / Math.pow(k, i)).toFixed(dm)) + ' ' + sizes[i];
    }
});
