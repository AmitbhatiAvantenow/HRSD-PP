document.addEventListener('DOMContentLoaded', function () {
    document.querySelectorAll('.dp-dropzone').forEach(function (zone) {
        var input = zone.querySelector('.dp-file-input');
        var nameEl = zone.querySelector('.dp-file-name');
        if (!input) return;

        var showName = function () {
            if (input.files && input.files[0]) {
                nameEl.textContent = input.files[0].name;
            }
        };
        input.addEventListener('change', showName);

        ['dragover', 'dragenter'].forEach(function (evt) {
            zone.addEventListener(evt, function (e) {
                e.preventDefault();
                zone.classList.add('dp-dragover');
            });
        });
        ['dragleave', 'drop'].forEach(function (evt) {
            zone.addEventListener(evt, function (e) {
                e.preventDefault();
                zone.classList.remove('dp-dragover');
            });
        });
        zone.addEventListener('drop', function (e) {
            if (e.dataTransfer && e.dataTransfer.files && e.dataTransfer.files.length) {
                input.files = e.dataTransfer.files;
                showName();
            }
        });
    });
});
