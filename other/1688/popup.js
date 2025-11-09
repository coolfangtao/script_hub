// --- 1. 核心配置 ---
const SELECTORS = {
    category: {
        container: ".space-common-offerlist",
        nextButton: ".fui-arrow.fui-next",
        disabledClass: "fui-disabled",
        captchaModal: "#nc_1_wrapper"
    },
    ranking: {
        container: "#pc-home2024-recommend-part",
        captchaModal: "#nc_1_wrapper" // 假设验证码选择器相同
    }
};

// --- 2. 可注入函数 (在1688页面环境中执行) ---

/**
 * [模式1: 类目] 采集当前页并点击“下一页”。
 * (已更新: 使用 MutationObserver 确保所有懒加载完成)
 * @param {object} selectors - 'category' 模式的选择器
 * @returns {Promise<object>}
 */
async function scrapeCategoryPageAndAdvance(selectors) {
    const sleep = (ms) => new Promise(resolve => setTimeout(resolve, ms));
    let html = "";
    let stopReason = "unknown";
    let hasNext = false;

    try {
        // 1. 检查验证码
        const captcha = document.querySelector(selectors.captchaModal);
        if (captcha && window.getComputedStyle(captcha).display !== 'none') {
            stopReason = "captcha";
            return { html, hasNext, stopReason, error: null };
        }

        // 2. 找到关键容器
        const container = document.querySelector(selectors.container);
        if (!container) {
            throw new Error("找不到商品容器。选择器可能已失效。");
        }

        // --- 3. (全新) 终极懒加载处理：MutationObserver ---

        // (此Promise将在内容稳定后被 resolve)
        const stablePromise = new Promise((resolve, reject) => {
            let stableTimer = null; // 稳定计时器
            const STABLE_WAIT_TIME = 3500; // (关键) 3.5秒内没动静=稳定

            const observer = new MutationObserver(() => {
                // 只要检测到DOM变化（即有新商品加载）：
                // 就重置“稳定”计时器
                clearTimeout(stableTimer);
                stableTimer = setTimeout(() => {
                    // 如果 3.5 秒后此计时器仍然运行，说明DOM已稳定
                    observer.disconnect(); // 停止监视
                    resolve(); // 宣布“已稳定”
                }, STABLE_WAIT_TIME);
            });

            // 开始监视：监视容器的“子列表”和“子树”
            observer.observe(container, {
                childList: true, // 监视子节点的添加/删除
                subtree: true    // 监视所有后代节点
            });

            // --- 触发懒加载 ---
            // A. 积极地滚动几次，确保触发所有加载
            window.scrollTo(0, document.body.scrollHeight);
            sleep(500).then(() => window.scrollBy(0, -300));
            sleep(1000).then(() => window.scrollTo(0, document.body.scrollHeight));

            // B. (关键) 启动第一个“稳定”计时器
            // 这用于处理两种情况：
            // 1. 页面根本没有懒加载（所有60个已显示），此时不会有mutation。
            // 2. 懒加载已触发，我们在等待 3.5 秒的“静默期”。
            stableTimer = setTimeout(() => {
                observer.disconnect();
                resolve();
            }, STABLE_WAIT_TIME);
        });

        // (设置一个20秒的“兜底”超时，防止页面bug导致无限等待)
        await Promise.race([
            stablePromise,         // 等待“稳定”信号
            sleep(20000)           // 或最多等待20秒
        ]);

        // --- 稳定逻辑结束 ---


        // 4. 采集HTML (此时100%是完整的)
        html = container.innerHTML;

        // 5. 查找“下一页”按钮
        const nextButton = document.querySelector(selectors.nextButton);
        if (nextButton && !nextButton.classList.contains(selectors.disabledClass)) {
            hasNext = true;
            stopReason = "progress";
            nextButton.click(); // 为下一次循环点击“下一页”
        } else {
            hasNext = false;
            stopReason = "endOfPages";
        }
        return { html, hasNext, stopReason, error: null };

    } catch (e) {
        return { html: "", hasNext: false, stopReason: "error", error: e.message };
    }
}

/**
 * [模式2: 榜单] 滚动到底部以加载所有商品，然后采集。
 * (此函数无变动)
 */
async function scrapeRankingPageByScrolling(selectors) {
    const sleep = (ms) => new Promise(resolve => setTimeout(resolve, ms));
    let lastHeight = -1;
    let currentHeight = 0;
    let noChangeCount = 0;

    try {
        for (let i = 0; i < 50; i++) {
            const captcha = document.querySelector(selectors.captchaModal);
            if (captcha && window.getComputedStyle(captcha).display !== 'none') {
                return { html: "", stopReason: "captcha", error: "滚动中遇到验证码" };
            }
            lastHeight = document.body.scrollHeight;
            window.scrollTo(0, document.body.scrollHeight);
            await sleep(1500 + Math.random() * 500);
            currentHeight = document.body.scrollHeight;
            if (currentHeight === lastHeight) {
                noChangeCount++;
                if (noChangeCount >= 3) {
                    break;
                }
            } else {
                noChangeCount = 0;
            }
        }
        const container = document.querySelector(selectors.container);
        if (container) {
            return { html: container.innerHTML, stopReason: "complete", error: null };
        } else {
            throw new Error("找不到榜单容器。选择器可能已失效。");
        }
    } catch (e) {
        return { html: "", stopReason: "error", error: e.message };
    }
}


// --- 3. Popup 助手函数 (无变动) ---

function setStatus(message, type = 'info') {
    const statusEl = document.getElementById('status');
    statusEl.textContent = message;
    switch (type) {
        case 'success':
            statusEl.className = "text-center text-sm font-medium text-green-700 h-6";
            break;
        case 'warning':
            statusEl.className = "text-center text-sm font-medium text-yellow-700 h-6";
            break;
        case 'error':
            statusEl.className = "text-center text-sm font-medium text-red-700 h-6";
            break;
        case 'info':
        default:
            statusEl.className = "text-center text-sm font-medium text-blue-700 h-6";
            break;
    }
}

function downloadHtml(html, mode, pageCount) {
    const blob = new Blob([html], { type: 'text/html' });
    const url = URL.createObjectURL(blob);
    const date = new Date();
    const f_date = `${date.getFullYear()}-${(date.getMonth() + 1).toString().padStart(2, '0')}-${date.getDate().toString().padStart(2, '0')}`;
    const filename = `1688-${mode}-${f_date}-p${pageCount}.html`;
    chrome.downloads.download({
        url: url,
        filename: filename
    });
}


// --- 4. 主采集处理器 (无变动) ---

async function runCategoryScrape(tab, maxPages) {
    let allHtml = "";
    let pageCount = 0;
    let hasNextPage = true;
    let stopReason = "unknown";

    while (hasNextPage && pageCount < maxPages) {
        pageCount++;
        setStatus(`采集中... 第 ${pageCount} / ${maxPages === 999 ? '?' : maxPages} 页...`, 'info');

        const results = await chrome.scripting.executeScript({
            target: { tabId: tab.id },
            func: scrapeCategoryPageAndAdvance, // (现在调用的是更新后的函数)
            args: [SELECTORS.category]
        });

        const { html, hasNext, stopReason: reason, error } = results[0].result;
        if (error) throw new Error(error);

        allHtml += html;
        hasNextPage = hasNext;
        stopReason = reason;

        if (stopReason === 'captcha') {
            pageCount--; //
            break;
        }
        if (stopReason === 'endOfPages') {
            break;
        }
        if (hasNextPage) {
            await new Promise(resolve => setTimeout(resolve, Math.random() * 2000 + 3000));
        }
    }

    if (stopReason !== 'captcha' && stopReason !== 'endOfPages' && pageCount === maxPages) {
        stopReason = "maxPages";
    }

    return { allHtml, pageCount, stopReason };
}

async function runRankingScrape(tab) {
    setStatus("开始滚动采集榜单...", 'info');

    const results = await chrome.scripting.executeScript({
        target: { tabId: tab.id },
        func: scrapeRankingPageByScrolling,
        args: [SELECTORS.ranking]
    });

    const { html, stopReason, error } = results[0].result;
    if (error) throw new Error(error);

    return { allHtml: html, pageCount: 1, stopReason };
}


// --- 5. DOM 监听器 (无变动) ---

document.addEventListener('DOMContentLoaded', () => {
    const scrapeButton = document.getElementById('scrapeButton');
    const pageLimitInput = document.getElementById('pageLimitInput');
    const categoryOptions = document.getElementById('categoryOptions');
    const modeCategory = document.getElementById('modeCategory');
    const modeRanking = document.getElementById('modeRanking');

    function updateModeUI() {
        if (modeCategory.checked) {
            categoryOptions.style.display = 'block';
        } else {
            categoryOptions.style.display = 'none';
        }
    }
    modeCategory.addEventListener('change', updateModeUI);
    modeRanking.addEventListener('change', updateModeUI);
    updateModeUI();

    scrapeButton.addEventListener('click', async () => {
        scrapeButton.disabled = true;
        setStatus("准备中...", 'info');

        try {
            const [tab] = await chrome.tabs.query({
                active: true,
                currentWindow: true,
                url: "https://*.1688.com/*"
            });

            if (!tab) {
                throw new Error("请先打开一个1688的页面。");
            }

            const selectedMode = document.querySelector('input[name="scrapeMode"]:checked').value;
            let result;

            if (selectedMode === 'category') {
                let maxPages = parseInt(pageLimitInput.value, 10);
                if (isNaN(maxPages) || maxPages < 1) {
                    maxPages = 999;
                }
                result = await runCategoryScrape(tab, maxPages);

            } else if (selectedMode === 'ranking') {
                result = await runRankingScrape(tab);
            }

            const { allHtml, pageCount, stopReason } = result;

            if (!allHtml || allHtml.trim() === "") {
                if (stopReason === 'captcha' && pageCount > 0) {
                   // ...
                } else if(stopReason === 'captcha' && pageCount === 0) {
                    throw new Error("在第1页(或滚动开始时)就遇到了验证码。");
                } else {
                    throw new Error("采集到了0个商品，请检查选择器。");
                }
            }

            downloadHtml(allHtml, selectedMode, pageCount);

            if (selectedMode === 'category') {
                if (stopReason === 'captcha') {
                    setStatus(`采集 ${pageCount} 页后遇验证码停止。已下载。`, 'warning');
                } else if (stopReason === 'maxPages') {
                    setStatus(`已达 ${pageCount} 页上限。已下载。`, 'success');
                } else {
                    setStatus(`已采集 ${pageCount} 页！已下载。`, 'success');
                }
            } else if (selectedMode === 'ranking') {
                if (stopReason === 'captcha') {
                    setStatus(`滚动中遇验证码停止。已下载(可能不全)。`, 'warning');
                } else {
                    setStatus(`榜单采集完毕！已下载。`, 'success');
                }
            }

        } catch (e) {
            console.error(e);
            setStatus(`错误: ${e.message}`, 'error');
        } finally {
            scrapeButton.disabled = false;
        }
    });
});