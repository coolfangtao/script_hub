// 获取 DOM 元素
const scrapeButton = document.getElementById('scrapeButton');
const buttonText = document.getElementById('buttonText');
const loadingIndicator = document.getElementById('loadingIndicator');
const statusMessage = document.getElementById('statusMessage');
// 新增：获取导出格式选择器
const exportFormatSelector = document.getElementById('exportFormat');

// 更新 UI 状态
function updateStatus(text, type = 'info') {
    const statusIcon = statusMessage.querySelector('.status-icon');
    const statusText = statusMessage.querySelector('.status-text');

    if (!statusIcon || !statusText) {
        // 兼容旧的 HTML 结构（如果存在）
        statusMessage.textContent = text;
    } else {
        statusText.textContent = text;
    }

    statusMessage.className = 'mt-4 p-3 text-sm rounded-lg border flex items-start gap-3'; // 重置类名
    statusMessage.classList.remove('hidden');

    let iconSvg = '';

    if (type === 'info') {
        statusMessage.classList.add('text-blue-800', 'bg-blue-50', 'border-blue-300');
        // 信息图标 (heroicons)
        iconSvg = `<svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" /></svg>`;
    } else if (type === 'success') {
        statusMessage.classList.add('text-green-800', 'bg-green-50', 'border-green-300');
        // 成功图标 (heroicons)
        iconSvg = `<svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" /></svg>`;
    } else if (type === 'error') {
        statusMessage.classList.add('text-red-800', 'bg-red-50', 'border-red-300');
        // 错误图标 (heroicons)
        iconSvg = `<svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" /></svg>`;
    }

    if (statusIcon) {
        statusIcon.innerHTML = iconSvg;
    }
}

// 核心点击事件监听器
scrapeButton.addEventListener('click', async () => {
    // 新增：获取用户选择的导出格式
    const exportFormat = exportFormatSelector ? exportFormatSelector.value : 'json';

    // 禁用按钮并显示加载中 (作为临时状态)
    scrapeButton.disabled = true;
    loadingIndicator.classList.remove('hidden');
    buttonText.textContent = '处理中...';
    updateStatus('正在向页面发送抓取指令...', 'info');

    let isButtonReset = false; // 增加一个标记，用于判断是否已重置

    try {
        // 1. 获取当前活动标签页
        let [tab] = await chrome.tabs.query({ active: true, currentWindow: true });

        if (!tab || !tab.url.includes('amazon.')) {
            updateStatus('请在亚马逊商品页面或评论页面上使用此插件。', 'error');
            // 重置按钮状态
            scrapeButton.disabled = false;
            loadingIndicator.classList.add('hidden');
            buttonText.textContent = '开始抓取';
            isButtonReset = true;
            return;
        }

        // 2. 向内容脚本发送消息，启动抓取
        const response = await chrome.tabs.sendMessage(tab.id, {
            action: "scrapeData",
            url: tab.url
        });

        if (response && response.status === 'success') {
            updateStatus(`抓取成功！共找到 ${response.data.totalReviewsExtracted} 条评论。正在下载 ${exportFormat.toUpperCase()} 文件...`, 'success');

            // 3. 使用 chrome.downloads API 触发下载
            // 关键修改：将格式传递给 downloadData
            downloadData(response.data, exportFormat);

            // 成功状态重置按钮
            scrapeButton.disabled = false;
            loadingIndicator.classList.add('hidden');
            buttonText.textContent = '开始抓取';
            isButtonReset = true;

        } else if (response && response.status === 'navigating') {
            // Content Script 正在导航到评论页，等待用户操作
            updateStatus('已点击“查看所有评论”，请等待页面加载完成并再次点击按钮。', 'info');

            // 🚀 关键修复：确保在导航状态下，按钮被启用，加载圈被隐藏
            scrapeButton.disabled = false;
            loadingIndicator.classList.add('hidden');
            buttonText.textContent = '再次点击启动抓取'; // 明确提示用户下一步
            isButtonReset = true;

        } else if (response && response.status === 'error') {
            updateStatus(`抓取失败: ${response.message}`, 'error');
            // 错误状态重置按钮
            scrapeButton.disabled = false;
            loadingIndicator.classList.add('hidden');
            buttonText.textContent = '开始抓取';
            isButtonReset = true;
        } else {
             updateStatus('未收到内容脚本响应，请刷新页面后重试。', 'error');
             // 错误状态重置按钮
             scrapeButton.disabled = false;
             loadingIndicator.classList.add('hidden');
             buttonText.textContent = '开始抓取';
             isButtonReset = true;
        }

    } catch (error) {
        console.error("Popup error:", error);
        updateStatus('发送指令失败或页面没有加载内容脚本。', 'error');
        // 确保发生错误时也重置按钮状态
        scrapeButton.disabled = false;
        loadingIndicator.classList.add('hidden');
        buttonText.textContent = '开始抓取';
        isButtonReset = true;
    }
});


/**
 * 将抓取到的数据转换为 CSV 格式的字符串。
 * @param {Object} data - 抓取到的数据对象
 * @returns {string} CSV 格式的字符串
 */
function convertToCsv(data) {
    if (!data.reviews || data.reviews.length === 0) {
        return "Review ID,Reviewer Name,Rating,Review Text,Product Title,Product Price,Product URL\nNo reviews found,,,,,,";
    }

    // CSV 头部
    const headers = ["Review ID", "Reviewer Name", "Rating", "Review Text", "Image URLs", "Product Title", "Product Price", "Product URL"];
    const headerRow = headers.join(',');

    // 辅助函数：清理并包裹特殊字符
    const cleanAndQuote = (str) => {
        if (typeof str !== 'string') str = String(str || '');
        // 移除内部换行符，并对包含特殊字符的字符串加双引号
        const cleaned = str.replace(/\r?\n|\r/g, ' ').trim();
        // 如果包含逗号、引号或换行符，需要包裹双引号，并转义内部引号
        if (cleaned.includes(',') || cleaned.includes('"')) {
            return `"${cleaned.replace(/"/g, '""')}"`;
        }
        return cleaned;
    };

    const rows = data.reviews.map(review => {
        const imageUrls = review.imageUrls && review.imageUrls.length > 0 ? review.imageUrls.join(' | ') : '';
        return [
            cleanAndQuote(review.reviewId),
            cleanAndQuote(review.reviewerName),
            cleanAndQuote(review.rating),
            cleanAndQuote(review.text),
            cleanAndQuote(imageUrls),
            cleanAndQuote(data.product.title || 'N/A'),
            cleanAndQuote(data.product.price || 'N/A'),
            cleanAndQuote(data.product.url || 'N/A')
        ].join(',');
    });

    return headerRow + '\n' + rows.join('\n');
}

/**
 * 将抓取到的数据转换为 TXT 格式的摘要。
 * @param {Object} data - 抓取到的数据对象
 * @returns {string} TXT 格式的字符串
 */
function convertToTxt(data) {
    let txt = `======================================\n`;
    txt += `  亚马逊商品评论摘要报告\n`;
    txt += `======================================\n`;
    txt += `商品标题: ${data.product.title || 'N/A'}\n`;
    txt += `商品价格: ${data.product.price || 'N/A'}\n`;
    txt += `商品链接: ${data.product.url || 'N/A'}\n`;
    txt += `总评论数: ${data.totalReviewsExtracted} 条\n`;
    txt += `--------------------------------------\n\n`;

    data.reviews.forEach((review, index) => {
        txt += `[${index + 1}] 评论人: ${review.reviewerName || 'Anonymous'}\n`;
        txt += `    评级: ${review.rating || 'N/A'}\n`;

        // 关键修改：移除长度限制，仅移除换行符
        const reviewText = review.text || 'N/A';
        txt += `    内容: ${reviewText.replace(/\r?\n|\r/g, ' ').trim()}\n`;

        // 关键新增：添加图片链接输出
        if (review.imageUrls && review.imageUrls.length > 0) {
             txt += `    图片数: ${review.imageUrls.length}\n`;
             // 输出所有图片链接，每行一个
             review.imageUrls.forEach((url, i) => {
                 txt += `    - 图片链接 ${i + 1}: ${url}\n`;
             });
        }
        txt += `\n`;
    });

    return txt;
}


/**
 * 使用 Chrome Downloads API 下载文件。
 * @param {Object} data - 要下载的数据对象
 * @param {string} format - 下载格式 ('json', 'csv', 'txt')
 */
function downloadData(data, format) {
    let fileContent = '';
    let mimeType = '';
    let fileExtension = '';

    // 确保有一个基本的文件名，并清理特殊字符
    let filenameBase = `amazon_${data.product && data.product.title ? data.product.title.substring(0, 30).replace(/[^a-zA-Z0-9\u4e00-\u9fa5]/g, '_') : 'data'}_reviews`;

    if (format === 'csv') {
        fileContent = convertToCsv(data);
        mimeType = 'text/csv';
        fileExtension = '.csv';
    } else if (format === 'txt') {
        fileContent = convertToTxt(data);
        // 使用 UTF-8 编码确保中文正确显示
        mimeType = 'text/plain;charset=utf-8';
        fileExtension = '.txt';
    } else { // 默认为 JSON
        fileContent = JSON.stringify(data, null, 2);
        mimeType = 'application/json';
        fileExtension = '.json';
    }

    const filename = `${filenameBase}${fileExtension}`;

    // 创建 Blob
    const blob = new Blob([fileContent], { type: mimeType });
    const url = URL.createObjectURL(blob);

    // 使用 chrome.downloads.download 进行下载
    chrome.downloads.download({
        url: url,
        filename: filename,
        saveAs: true // 弹出保存对话框
    }, (downloadId) => {
        if (chrome.runtime.lastError) {
            console.error("Download failed:", chrome.runtime.lastError);
            updateStatus('文件下载失败，请检查权限。', 'error');
        }
        // 完成下载后释放临时 URL
        URL.revokeObjectURL(url);
    });
}
