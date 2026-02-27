document.addEventListener('DOMContentLoaded', async () => {
    // Получаем конфиг с сервера
    let MAX_FILE_SIZE_BYTES;
    try {
        const response = await fetch('/config');
        if (!response.ok) throw new Error('Не удалось получить конфигурацию');
        const config = await response.json();
        MAX_FILE_SIZE_BYTES = config.max_file_size 
    } catch (error) {
        console.error('Ошибка при получении конфигурации:', error);
        MAX_FILE_SIZE_BYTES = 500 * 1024 * 1024; // При ошибке получения - 500 мб по дефолту
    }

    const uploadForm = document.getElementById('uploadForm');
    const fileInput = document.getElementById('fileInput');
    const hoursInput = document.getElementById('hoursInput');
    const uploadButton = document.querySelector('.upload-button');
    const buttonText = uploadButton.querySelector('.button-text');
    const spinner = uploadButton.querySelector('.spinner');
    const messageArea = document.getElementById('messageArea');
    const fileNameDisplay = document.getElementById('fileName');
    const resultDiv = document.getElementById('result');
    const downloadLink = document.getElementById('download-link');
    const qrImage = document.getElementById('qr-image');

    let currentFileId = null;

    function updateFilesNames() {
        const files = fileInput.files;

        if (files.length === 0) {
            fileNameDisplay.textContent = 'Файл(ы) не выбраны';
        } else if (files.length === 1) {
            fileNameDisplay.textContent = files[0].name;
        } else {
            fileNameDisplay.textContent = `${files[0].name} и ещё ${files.length - 1}`;
        }
    }

    // Обновляем отображение файла
    fileInput.addEventListener('change', () => {
        updateFilesNames();
    });

    // Обработчик формы
    uploadForm.addEventListener('submit', async (event) => {
        event.preventDefault();

        const files = fileInput.files;
        const hours = parseInt(hoursInput.value, 10);

        messageArea.textContent = '';
        messageArea.className = 'message-area';

        if (!files.length) {
            showMessage('Пожалуйста, выберите хотя бы один файл.', 'error');
            return;
        }

        if (isNaN(hours) || hours < 1 || hours > 24) {
            showMessage('Срок хранения должен быть от 1 до 24 часов.', 'error');
            return;
        }

        // Проверяем суммарный размер (если доступен)
        let total_size_estimate = 0;
        let has_unknown_size = false;

        for (let i = 0; i < files.length; i++) {
            if (typeof files[i].size !== 'number') {
                has_unknown_size = true;
                break;
            }
            total_size_estimate += files[i].size;
        }

        if (!has_unknown_size && total_size_estimate > MAX_FILE_SIZE_BYTES) {
            showMessage(`Общий размер файлов не должен превышать ${MAX_FILE_SIZE_BYTES / (1024 * 1024)} МБ`, 'error');
            return;
        }

        // Загрузка спиннер
        buttonText.style.display = 'none';
        spinner.style.display = 'inline-block';
        uploadButton.disabled = true;

        try {
            const formData = new FormData();

            for (let file of files) {
                formData.append("uploaded_files", file); 
            }
            formData.append("avail_period", hours);

            const response = await fetch('/upload', {
                method: 'POST',
                body: formData
            });

            if (!response.ok) {
                throw new Error('Ошибка сети или сервера');
            }

            const data = await response.json();

            showMessage(files.length === 1 ? `Файл "${files[0].name}" успешно загружен.` : `Файлы объединены в ZIP и загружены.` , 'success');

            const downloadUrl = `${window.location.origin}${data.download_link}`;
            const qrCodeUrl = data.qr_code;

            downloadLink.href = downloadUrl;
            downloadLink.textContent = downloadUrl;

            const qrBlob = await fetch(qrCodeUrl).then(res => res.blob());
            qrImage.src = URL.createObjectURL(qrBlob);

            resultDiv.style.display = 'block';
            uploadForm.style.display = 'none';

            currentFileId = data.download_link.split('/').pop();

            const deleteButton = document.getElementById('delete_btn');

            if (!deleteButton) {
                console.warn("Кнопка #delete_btn не найдена в DOM");
                return;
            }

            // Показываем кнопку
            deleteButton.style.display = 'inline-block';

            // Обработчик кнопки 1 раз (1 раз в жизни страницы.. и моей..)
            if (!deleteButton.dataset.listenerAdded) {
                deleteButton.addEventListener('click', async function () {
                    if (!currentFileId) {
                        console.warn("Нет текущего файла для удаления");
                        return;
                    }
                        
                    // Визуальное состояние загрузки
                    const btnText   = deleteButton.querySelector('.button-text') || deleteButton;
                    const btnSpinner = deleteButton.querySelector('.spinner');
                    btnText.style.display = 'none';
                    if (btnSpinner) btnSpinner.style.display = 'inline-block';
                    deleteButton.disabled = true;

                    try {
                        const resp = await fetch(`/delete/${currentFileId}`, {
                            method: 'POST',
                            headers: { 'Accept': 'application/json' }
                        });
                        
                        // Пытаюсь показать текст ошибки от сервера (если пропишу его)
                        if (!resp.ok) {
                            let msg = 'Не удалось удалить файл';
                            try {
                                const err = await resp.json();
                                msg = err.detail || msg;
                            } catch {}
                            throw new Error(msg);
                        }

                        showMessage('Файл успешно удалён', 'success');

                        setTimeout(() => {
                            if (messageArea.textContent === 'Файл успешно удалён') {
                                messageArea.textContent = '';
                                messageArea.className = 'message-area'; 
                            }
                        }, 5000);

                        // Сброс состояния страницы
                        resultDiv.style.display = 'none';
                        uploadForm.style.display = 'block';
                        deleteButton.style.display = 'none';

                        currentFileId = null;
                        qrImage.src = '';
                        downloadLink.href = '';
                        downloadLink.textContent = '';

                        fileInput.value = '';
                        updateFilesNames();

                    } catch (err) {
                        showMessage(`Ошибка: ${err.message}`, 'error');
                        console.error(err);
                    } finally {
                        btnText.style.display = 'inline-block';
                        if (btnSpinner) btnSpinner.style.display = 'none';
                        deleteButton.disabled = false;
                    }
                });

                // Флажок, что слушатель уже повешен
                deleteButton.dataset.listenerAdded = 'true';
            }

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
        messageArea.className = `message-area ${type}`;
    }

    function formatFileSize(bytes, decimals = 2) {
        if (bytes === 0) return '0 Bytes';
        const k = 1024;
        const dm = decimals < 0 ? 0 : decimals;
        const sizes = ['Bytes', 'KB', 'MB', 'GB', 'TB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        return parseFloat((bytes / Math.pow(k, i)).toFixed(dm)) + ' ' + sizes[i];
    }

    /* Drag&Drop */
    function handleDragOver(event){
        event.preventDefault(); //Предотвращаем стандартное поведение браузера
        uploadForm.classList.add('drag-over'); // Добавляем класс для CSS
    }
        
    function handleDrop(event){
        event.preventDefault();
        uploadForm.classList.remove('drag-over'); // Убираем класс после сброса файлов

        const files = event.dataTransfer.files;
        if (files.length > 0) {
            
            fileInput.files = files; // Выбранные файлы - input[type="file"]
        
            if (files.length > 0) {
                fileInput.files = files; 
                updateFilesNames();
            }
        }
    } 

    function handleDragEnter(event) {
        event.preventDefault();
        uploadForm.classList.add('drag-over');
    }

    function handleDragLeave(event) {
        event.preventDefault();
        uploadForm.classList.remove('drag-over');
    }

    uploadForm.addEventListener('dragover', handleDragOver);
    uploadForm.addEventListener('drop', handleDrop);
    uploadForm.addEventListener('dragenter', handleDragEnter);
    uploadForm.addEventListener('dragleave', handleDragLeave);

});



