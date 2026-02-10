<script src="/static/scripts/jquery-1.10.2.js"></script>
<!-- <script src="/static/scripts/bootstrap.js"></script> -->
<script src="/static/scripts/respond.js"></script>
<script src="https://cdnjs.cloudflare.com/ajax/libs/cropperjs/1.6.1/cropper.min.js"></script>
<script>
    window.onload = function () {
        // 延迟300ms确保动画流畅（可选）
        setTimeout(() => {
            const overlay = document.getElementById('_loading-overlay');
            const content = document.getElementById('_content');

            // 隐藏遮罩层（淡出效果由CSS transition实现）
            overlay.style.opacity = '0';

            // 显示内容并触发动画
            setTimeout(() => {
                overlay.style.display = 'none';
                content.classList.add('show');
            }, 500); // 等待遮罩层淡出完成
        }, 300);
    };
</script>