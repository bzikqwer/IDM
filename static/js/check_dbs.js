// Интервал в миллисекундах (5 минут = 300000 мс)
const REFRESH_INTERVAL = 2 * 60 * 1000;

// Функция, которая делает запрос к /api/check-dbs и обновляет страницу
function fetchDbsInfo() {
    fetch("/api/check-dbs")
        .then(response => response.json())
        .then(data => {
            // data — массив вида [{db_name, unavailable, incomplete_count}, ...]
            let html = '<ul>';
            data.forEach(db => {
                if (db.unavailable) {
                    html += `<li><strong>${db.db_name}</strong>: база недоступна</li>`;
                } else {
                    if (db.incomplete_count === 0) {
                        html += `<li><strong>${db.db_name}</strong>: все пользователи заполнены</li>`;
                    } else {
                        html += `<li><strong>${db.db_name}</strong>: незаполненных пользователей — ${db.incomplete_count}</li>`;
                    }
                }
            });
            html += '</ul>';

            const infoBlock = document.getElementById('db-info-block');
            const infoContent = document.getElementById('db-info-content');
            infoContent.innerHTML = html;
            infoBlock.style.display = 'block';
        })
        .catch(err => {
            console.error('Ошибка запроса /api/check-dbs:', err);
            const infoBlock = document.getElementById('db-info-block');
            infoBlock.style.display = 'block';
            infoBlock.innerHTML = '<div class="alert-error">Ошибка при загрузке данных о базах</div>';
        });
}

document.addEventListener('DOMContentLoaded', function() {
    // 1) Сразу делаем первый запрос
    fetchDbsInfo();

    // 2) Запускаем интервал: повторять запрос каждые 5 минут
    setInterval(fetchDbsInfo, REFRESH_INTERVAL);
});
