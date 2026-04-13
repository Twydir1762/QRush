document.addEventListener('DOMContentLoaded', async () => {
    const fileInfo = document.getElementById('fileInfo');
    const fileNameEl = document.getElementById('fileName');
    const fileSizeEl = document.getElementById('fileSize');
    const uploadTimeEl = document.getElementById('uploadTime');
    const expirationTimeEl = document.getElementById('expirationTime');
    const contentDetails = document.getElementById('contentDetails');
    const contentList = document.getElementById('contentList');
    const downloadBtn = document.getElementById('downloadBtn');
    const downloadBtnText = downloadBtn.querySelector('.button-text');
    const downloadBtnSpinner = downloadBtn.querySelector('.spinner');

    function formatFileSize(bytes, decimals = 2) {
        if (bytes === 0) return '0 Bytes';
        const k = 1024;
        const dm = decimals < 0 ? 0 : decimals;
        const sizes = ['Bytes', 'KB', 'MB', 'GB', 'TB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        return parseFloat((bytes / Math.pow(k, i)).toFixed(dm)) + ' ' + sizes[i];
    }

    function formatDateTime(isoString) {
        const utcString = isoString.includes('Z') ? isoString : isoString + 'Z';
        const date = new Date(utcString);
        const timeString = date.toLocaleString('ru-RU', {
            year: 'numeric',
            month: 'long',
            day: 'numeric'
        });
        const time = date.toLocaleString('ru-RU', {
            hour: '2-digit',
            minute: '2-digit',
            second: '2-digit'
        });
        return `${timeString} ${time}`;
    }

    // file_id из URL
    const fileId = window.location.pathname.split('/').pop();

    if (!fileId) {
        showError('Некорректная ссылка');
        return;
    }

    async function loadFileInfo() {
        try {
            const response = await fetch(`/file/${fileId}`);

            if (!response.ok) {
                if (response.status === 404) {
                    showNotFound();
                } else {
                    showError('Ошибка при получении информации о файле');
                }
                return;
            }

            const fileData = await response.json();

            // Информацию о файле
            fileNameEl.textContent = `📥 ${fileData.filename}`;
            fileSizeEl.textContent = `Размер: ${formatFileSize(fileData.size)}`;
            uploadTimeEl.innerHTML = `Загружено: ${formatDateTime(fileData.upload_time)}`;
            expirationTimeEl.innerHTML = `Действителен до: ${formatDateTime(fileData.expiration_time)}`;

            // Если несколько файлов в архиве - показываем содержимое
            if (fileData.content && fileData.content.length > 1) {
                contentDetails.style.display = 'block';
                contentList.innerHTML = fileData.content
                    .map(item => `<div style="padding: 8px 0; border-bottom: 1px solid rgba(0, 0, 0, 0.05);">
                        📄 ${item.orig_name} <span style="color: rgba(0, 0, 0, 0.6);">(${formatFileSize(item.size)})</span>
                    </div>`)
                    .join('');
            }

            // Слушатель на кнопку скачивания
            setupDownloadButton(fileData.filename);

        } catch (error) {
            console.error('Ошибка при загрузке информации о файле:', error);
            showError('Произошла ошибка при загрузке информации о файле');
        }
    }

    function setupDownloadButton(filename) {
        downloadBtn.addEventListener('click', async () => {
            downloadBtnText.style.display = 'none';
            downloadBtnSpinner.style.display = 'inline-block';
            downloadBtn.disabled = true;

            try {
                const response = await fetch(`/download/${fileId}/file`);

                if (!response.ok) {
                    if (response.status === 404) {
                        showNotFound();
                    } else {
                        showError('Ошибка при скачивании файла');
                    }
                    return;
                }

                // Скачиваем файл
                const blob = await response.blob();
                const downloadUrl = window.URL.createObjectURL(blob);
                const a = document.createElement('a');
                a.href = downloadUrl;
                a.download = filename;
                document.body.appendChild(a);
                a.click();
                window.URL.revokeObjectURL(downloadUrl);
                document.body.removeChild(a);

            } catch (error) {
                console.error('Ошибка при скачивании файла:', error);
                showError('Произошла ошибка при скачивании файла');
            } finally {
                downloadBtnText.style.display = 'inline-block';
                downloadBtnSpinner.style.display = 'none';
                downloadBtn.disabled = false;
            }
        });
    }

    function showError(message) {
        fileInfo.innerHTML = `
            <h2 style="margin-bottom: 10px;">⚠️ Ошибка</h2>
            <p style="margin-bottom: 20px;">${message}</p>
            <a href="/" class="upload-button" style="text-decoration: none; display: inline-block; width: 220px; margin-top: 10px;">
                На главную
            </a>
        `;
    }

    function showNotFound() {
        // Загружаем not_found.html
        fetch('/static/not_found.html')
            .then(res => res.text())
            .then(html => {
                document.documentElement.innerHTML = html;
            })
            .catch(() => {
                showError('Файл не найден');
            });
    }

    // Загружаем информацию о файле при загрузке страницы
    loadFileInfo();
});
