// -------------------------------------------------------------------
// 用户提供的关键选择器 (已调整为更通用的模式)
// -------------------------------------------------------------------
const SELECTORS = {
    // 通常在商品详情页
    PRODUCT_TITLE: '#productTitle',
    // PRODUCT_PRICE: '#priceblock_ourprice', // 旧的通用价格选择器

    // **新版价格结构的选择器**
    PRODUCT_PRICE_WHOLE: '#corePriceDisplay_desktop_feature_div .a-price-whole',
    PRODUCT_PRICE_FRACTION: '#corePriceDisplay_desktop_feature_div .a-price-fraction',

    // 跳转到评论页面按钮：通常在商品详情页
    SEE_MORE_REVIEWS_BUTTON: '#reviews-medley-footer a',

    // 评论容器和内容：在评论详情页
    REVIEW_CONTAINER: '[data-hook="review"]', // 匹配所有评论卡片
    REVIEW_TEXT: '.review-text-content', // 评论文本的通用类

    // ⭐ 评级：修复 -> 使用最通用的类名，避免被 data-hook 属性的变化影响
    REVIEW_RATING: '.review-rating',

    // ⭐ 评论人名：使用最稳定的类名 a-profile-name，它通常在 a-profile-content 内部
    REVIEWER_NAME: '.a-profile-name',

    // ⭐ 评论图片：使用 data-hook 来定位评论图片元素
    REVIEW_IMAGE: '[data-hook="review-image-tile"]',

    // 翻页按钮：在评论详情页
    NEXT_PAGE_BUTTON: '#cm_cr-pagination_bar > ul > li.a-last > a',
};
// -------------------------------------------------------------------

// 用于引入延迟以应对反爬机制和等待 DOM 渲染
const delay = ms => new Promise(resolve => setTimeout(resolve, ms));
let totalReviews = [];
let currentPage = 1;

// **新增：用于本地存储的键名**
const STORAGE_KEY = 'amazonScraperProductInfo';


/**
 * 根据亚马逊缩略图 URL 规律，尝试获取高清图片 URL。
 * 亚马逊高清图通常是通过移除 URL 中尺寸标记（如 ._SY88）来实现。
 * @param {string} thumbUrl - 缩略图 URL
 * @returns {string} 潜在的高清图 URL
 */
function getHighResImageUrl(thumbUrl) {
    if (!thumbUrl) return 'URL_N/A';
    // 匹配并移除任何尺寸标记，例如 ._SY88_ 或 ._SL75_ 等
    // 正则表达式: 匹配 [\._] 后跟着 1-4 个大写字母，再跟着 1-4 位数字，最后可选地跟着下划线
    const highResUrl = thumbUrl.replace(/[\._](S|s|S|L|X|T|P|C|B|W|H|I|E|F|K|M|R|Y)\d{1,4}_/g, '');
    // 最后的检查：移除可能残留的尺寸标记
    return highResUrl.replace(/\._[A-Z]{1,4}\d{1,4}_/g, '');
}


/**
 * 提取当前页面上的所有评论和静态数据。
 * @returns {Array<Object>} 当前页面的评论列表
 */
function extractReviewsFromCurrentPage() {
    const reviewElements = document.querySelectorAll(SELECTORS.REVIEW_CONTAINER);
    const reviews = [];

    reviewElements.forEach((el, index) => {
        try {
            // 提取评论文本
            const textElement = el.querySelector(SELECTORS.REVIEW_TEXT);
            const text = textElement ? textElement.textContent.trim() : 'N/A';

            // 提取星级（通常在 title 属性中）
            const ratingElement = el.querySelector(SELECTORS.REVIEW_RATING);
            let ratingText = 'N/A';

            if (ratingElement) {
                // ⭐ 优先级 1: 查找内部的 a-icon-alt span 元素，这是最直接的文本
                const altSpan = ratingElement.querySelector('.a-icon-alt');
                if (altSpan) {
                    ratingText = altSpan.textContent.trim();
                } else {
                    // 优先级 2 & 3: 如果没有内部 span，则回退到属性
                    ratingText = ratingElement.getAttribute('aria-label') || ratingElement.getAttribute('title');
                }
            }

            // ⭐ 提取评论人名
            const nameElement = el.querySelector(SELECTORS.REVIEWER_NAME);
            const reviewerName = nameElement ? nameElement.textContent.trim() : 'Anonymous';

            // ⭐ 提取评论图片（可能有多张，使用 querySelectorAll）
            const imageElements = el.querySelectorAll(SELECTORS.REVIEW_IMAGE);
            const imageUrls = Array.from(imageElements).map(imgEl => {
                // 评论图片元素本身可能是 img 标签，也可能是包含 img 的父级
                const imgTag = imgEl.tagName === 'IMG' ? imgEl : imgEl.querySelector('img');
                let thumbUrl = null;

                if (imgTag) {
                    // 1. 优先检查 data-a-hires (旧习惯，以防万一)
                    thumbUrl = imgTag.getAttribute('data-a-hires');

                    // 2. 如果没有 data-a-hires，则使用 src 属性（这是您提供的元素中唯一的 URL）
                    if (!thumbUrl) {
                        thumbUrl = imgTag.src;
                    }
                }

                // 3. 将缩略图 URL 转换为高清 URL
                return getHighResImageUrl(thumbUrl);

            }).filter(url => url && url !== 'URL_N/A' && !url.includes('.gif')); // 过滤掉无效或占位符

            reviews.push({
                reviewId: el.id || `Review_${Date.now()}_${index}`,
                page: currentPage,
                reviewerName: reviewerName, // 已添加
                rating: ratingText,
                text: text,
                imageUrls: imageUrls, // 已添加
            });
        } catch (e) {
            console.error("Error extracting review:", e);
        }
    });

    return reviews;
}

/**
 * 核心逻辑：循环点击下一页按钮并抓取所有数据。
 * @returns {Object} 抓取到的所有数据，包括商品信息和评论。
 */
async function scrapeReviewsLoop() {
    // 增加延迟，模拟人类操作，避免反爬
    const PAGE_DELAY_MS = 3000;

    // 检查是否在评论页面的函数
    const isOnReviewPage = () => document.querySelector(SELECTORS.NEXT_PAGE_BUTTON);

    if (!isOnReviewPage()) {
        throw new Error("当前页面不是评论详情页，无法开始分页抓取。请先导航到评论页。");
    }

    // **新增：从本地存储中获取商品信息**
    const productInfo = JSON.parse(localStorage.getItem(STORAGE_KEY) || '{}');

    let hasNextPage = true;
    while (hasNextPage) {
        // 1. 提取当前页数据
        const currentReviews = extractReviewsFromCurrentPage();
        totalReviews.push(...currentReviews);

        console.log(`已抓取第 ${currentPage} 页，总计 ${totalReviews.length} 条评论.`);

        // 2. 检查下一页按钮
        const nextButton = document.querySelector(SELECTORS.NEXT_PAGE_BUTTON);

        // 检查按钮是否存在，或是否为禁用状态 (a-disabled)
        if (!nextButton || nextButton.classList.contains('a-disabled') || nextButton.parentElement.classList.contains('a-disabled')) {
            hasNextPage = false;
            break;
        }

        // 3. 模拟点击下一页按钮
        nextButton.click();

        // 关键：等待新页面加载和反爬延迟
        await delay(PAGE_DELAY_MS);

        currentPage++;
    }

    // 4. 返回最终结果，使用存储的商品信息
    return {
        product: {
            title: productInfo.title || "N/A (Not scraped from main page)",
            price: productInfo.price || "N/A (Not scraped from main page)",
            url: productInfo.url || window.location.href,
        },
        totalReviewsExtracted: totalReviews.length,
        reviews: totalReviews
    };
}

/**
 * 监听来自 popup.js 的消息
 */
chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
    if (request.action === "scrapeData") {
        totalReviews = []; // 重置数据
        currentPage = 1;

        // 立即执行异步抓取函数，并使用 sendResponse 返回结果
        scrapeReviewsLoop()
            .then(data => {
                // **新增：抓取完成后清除存储的商品信息**
                localStorage.removeItem(STORAGE_KEY);
                sendResponse({ status: 'success', data: data });
            })
            .catch(error => {
                const seeMoreButton = document.querySelector(SELECTORS.SEE_MORE_REVIEWS_BUTTON);
                const isMainProductPage = seeMoreButton && !request.url.includes('customer-reviews');

                if (isMainProductPage) {
                     // 此时在商品详情页，需要跳转到评论页

                     // **新增：抓取商品信息并存储**
                     const productTitle = document.querySelector(SELECTORS.PRODUCT_TITLE)?.textContent.trim() || "N/A";

                     // ⭐ 新的价格抓取逻辑：组合整数和小数部分
                     const wholePriceElement = document.querySelector(SELECTORS.PRODUCT_PRICE_WHOLE);
                     const fractionPriceElement = document.querySelector(SELECTORS.PRODUCT_PRICE_FRACTION);
                     let productPrice = "N/A";

                     if (wholePriceElement && fractionPriceElement) {
                         // 获取货币符号（通常在 .a-price-symbol 中）
                         const symbolElement = wholePriceElement.previousElementSibling;
                         const currencySymbol = symbolElement ? symbolElement.textContent.trim() : '';

                         // 移除整数部分可能包含的货币千分位分隔符（如德语的 '.'），只保留数字
                         const whole = wholePriceElement.textContent.trim().replace(/\./g, '');
                         const fraction = fractionPriceElement.textContent.trim();

                         // 组合价格，使用标准的英文小数点 '.'
                         productPrice = `${currencySymbol} ${whole}.${fraction}`;

                     } else if (document.querySelector('#priceblock_ourprice')) {
                         // 兼容旧的/默认的价格块，以防新选择器失效
                         productPrice = document.querySelector('#priceblock_ourprice').textContent.trim();
                     }

                     const productInfo = {
                         title: productTitle,
                         price: productPrice,
                         url: request.url
                     };
                     localStorage.setItem(STORAGE_KEY, JSON.stringify(productInfo));

                     seeMoreButton.click();
                     sendResponse({ status: 'navigating', message: '已点击跳转到评论页，请等待页面加载后重新点击插件按钮。' });
                     return true; // 保持通道开放以进行异步响应（尽管这里不再需要后续响应）
                }

                sendResponse({ status: 'error', message: error.message });
            });

        // 必须返回 true 来指示 sendResponse 将被异步调用
        return true;
    }
});
