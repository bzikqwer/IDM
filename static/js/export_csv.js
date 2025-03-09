// export_csv.js

document.addEventListener('DOMContentLoaded', () => {
  const exportBtn = document.getElementById('export-csv-btn');
  if (exportBtn) {
    exportBtn.addEventListener('click', exportTableToCsv);
  }
});

function exportTableToCsv() {
  const table = document.getElementById('users-table');
  if (!table) return;

  const csvRows = [];
  // Заголовки CSV
  csvRows.push(['username', 'account_status', 'номер_заявки', 'описание'].join(';'));

  // Получаем все строки таблицы
  const rows = table.querySelectorAll('tbody tr');
  rows.forEach((tr) => {
    const username = tr.cells[0].innerText.trim();
    const accountStatus = tr.cells[1].innerText.trim();

    const nomerInput = tr.cells[2].querySelector('input');
    const opisanieInput = tr.cells[3].querySelector('input');

    const nomerZayavki = nomerInput ? nomerInput.value.trim() : '';
    const opisanie = opisanieInput ? opisanieInput.value.trim() : '';

    const rowData = [username, accountStatus, nomerZayavki, opisanie].join(';');
    csvRows.push(rowData);
  });

  // Здесь важный момент: добавляем '\uFEFF' в начало строки,
  // чтобы при открытии в Excel корректно отобразились русские символы
  const csvString = '\uFEFF' + csvRows.join('\n');

  const blob = new Blob([csvString], { type: 'text/csv;charset=utf-8;' });
  const url = URL.createObjectURL(blob);

  const link = document.createElement('a');
  link.href = url;
  // Имя файла
  link.download = 'users.csv';
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);

  URL.revokeObjectURL(url);
}
