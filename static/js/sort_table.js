// sort_table.js

document.addEventListener('DOMContentLoaded', function() {
    // Ищем заголовок для сортировки
    const statusHeader = document.getElementById('status-header');
    if (statusHeader) {
        statusHeader.addEventListener('click', sortTableByStatus);
    }
});

function sortTableByStatus() {
    const table = document.getElementById('users-table');
    if (!table) return;

    const tbody = table.querySelector('tbody');
    // Собираем все строки TR
    const rows = Array.from(tbody.querySelectorAll('tr'));

    // Делим на «незаполненные» (class="incomplete") и «остальные»
    const incompleteRows = rows.filter(row => row.classList.contains('incomplete'));
    const completeRows = rows.filter(row => !row.classList.contains('incomplete'));

    // Сортируем «остальные» по содержимому ячейки столбца Account Status (индекс 1)
    completeRows.sort((a, b) => {
        const statusA = a.cells[1].innerText.toLowerCase();
        const statusB = b.cells[1].innerText.toLowerCase();
        if (statusA < statusB) return -1;
        if (statusA > statusB) return 1;
        return 0;
    });

    // Очищаем tbody и добавляем обратно: сначала «незаполненные», потом отсортированные
    tbody.innerHTML = '';
    incompleteRows.forEach(row => tbody.appendChild(row));
    completeRows.forEach(row => tbody.appendChild(row));
}
