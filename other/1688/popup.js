// --- 1. 核心配置---
const SELECTORS = {
    category: {
        container: ".space-common-offerlist",
        nextButton: ".fui-arrow.fui-next",
        disabledClass: "fui-disabled",
        captchaModal: "#nc_1_wrapper"
    },
    ranking: {
        container: "#pc-home2024-recommend-part",
        captchaModal: "#nc_1_wrapper"
    },
    miaoshou: {
        // 关键数据行容器 (此选择器代表一行数据)
        dataRow: ".vue-recycle-scroller__item-wrapper > div",

        // 链接的选择器（相对于 dataRow）
        linkSelector: 'div:nth-child(4) div:nth-child(2) a',
        // 跳过原因的选择器（相对于 dataRow）
        reasonCellSelector: 'div:nth-child(7)',

        // 精确的下一页按钮选择器
        nextButton: "#appScrollContainer > div.pro-virtual-table > div.pro-pagination button.btn-next",
        // 禁用按钮的类名 (用于判断是否到最后一页)
        disabledClass: "is-disabled"
    }
};

// --- 2. 可注入函数 ---
async function scrapeCategoryPageAndAdvance(selectors) {
    const sleep = (ms) => new Promise(resolve => setTimeout(resolve, ms));
    let html = "";
    let stopReason = "unknown";
    let hasNext = false;

    try {
        const captcha = document.querySelector(selectors.captchaModal);
        if (captcha && window.getComputedStyle(captcha).display !== 'none') {
            stopReason = "captcha";
            return { html, hasNext, stopReason, error: null };
        }

        const container = document.querySelector(selectors.container);
        if (!container) {
            throw new Error("找不到商品容器。选择器可能已失效。");
        }

        const stablePromise = new Promise((resolve, reject) => {
            let stableTimer = null;
            const STABLE_WAIT_TIME = 3500;

            const observer = new MutationObserver(() => {
                clearTimeout(stableTimer);
                stableTimer = setTimeout(() => {
                    observer.disconnect();
                    resolve();
                }, STABLE_WAIT_TIME);
            });

            observer.observe(container, {
                childList: true,
                subtree: true
            });

            window.scrollTo(0, document.body.scrollHeight);
            sleep(500).then(() => window.scrollBy(0, -300));
            sleep(1000).then(() => window.scrollTo(0, document.body.scrollHeight));

            stableTimer = setTimeout(() => {
                observer.disconnect();
                resolve();
            }, STABLE_WAIT_TIME);
        });

        await Promise.race([
            stablePromise,
            sleep(20000)
        ]);

        html = container.innerHTML;

        const nextButton = document.querySelector(selectors.nextButton);
        if (nextButton && !nextButton.classList.contains(selectors.disabledClass)) {
            hasNext = true;
            stopReason = "progress";
            nextButton.click();
        } else {
            hasNext = false;
            stopReason = "endOfPages";
        }
        return { html, hasNext, stopReason, error: null };

    } catch (e) {
        return { html: "", hasNext: false, stopReason: "error", error: e.message };
    }
}


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


/**
 * [模式3: 妙手] 采集当前页并点击“下一页”。
 * @param {object} selectors - 'miaoshou' 模式的选择器
 * @returns {Promise<object>}
 */
async function scrapeMiaoshouPageAndAdvance(selectors) {
    const sleep = (ms) => new Promise(resolve => setTimeout(resolve, ms));
    const results = [];
    let hasNext = false;
    let stopReason = "progress";

    try {
        // 1. 确保虚拟列表内容已加载完毕
        // 即使是分页模式，妙手页面当前页的 20 个项目也可能需要短暂时间加载
        await sleep(1500 + Math.random() * 500);

        const rows = document.querySelectorAll(selectors.dataRow);

        rows.forEach(row => {
            const linkElement = row.querySelector(selectors.linkSelector);
            const reasonCell = row.querySelector(selectors.reasonCellSelector);

            if (linkElement && reasonCell) {
                const link = linkElement.href || '';
                const rawReasonText = reasonCell.textContent;

                // 过滤无效链接
                if (link.startsWith('http') && link.includes('1688.com')) {
                    const reason = rawReasonText.replace(/\s+/g, ' ').trim();

                    if (reason) {
                        results.push({ link, reason });
                    }
                }
            }
        });

        // 2. 查找并点击“下一页”按钮
        const nextButton = document.querySelector(selectors.nextButton);
        if (nextButton && !nextButton.classList.contains(selectors.disabledClass)) {
            hasNext = true;
            nextButton.click();
        } else {
            hasNext = false;
            stopReason = "endOfPages";
        }

        return { data: results, hasNext, stopReason, error: null };

    } catch (e) {
        return { data: [], hasNext: false, stopReason: "error", error: e.message };
    }
}


// --- 3. Popup 助手函数 ---
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

function downloadCsv(data) {
    const headers = ["链接", "跳过原因"];
    const csvContent = data.map(row =>
        `"${row.link.replace(/"/g, '""')}",` +
        `"${row.reason.replace(/"/g, '""')}"`
    ).join('\n');

    const finalCsv = headers.join(',') + '\n' + csvContent;

    const blob = new Blob([new Uint8Array([0xEF, 0xBB, 0xBF]), finalCsv], { type: 'text/csv;charset=utf-8' });
    const url = URL.createObjectURL(blob);
    const date = new Date();
    const f_date = `${date.getFullYear()}-${(date.getMonth() + 1).toString().padStart(2, '0')}-${date.getDate().toString().padStart(2, '0')}`;
    const filename = `miaoshou-skipped-links-${f_date}.csv`;

    chrome.downloads.download({
        url: url,
        filename: filename
    });
}


// --- 4. 主采集处理器 ---

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
            func: scrapeCategoryPageAndAdvance,
            args: [SELECTORS.category]
        });

        const { html, hasNext, stopReason: reason, error } = results[0].result;
        if (error) throw new Error(error);

        allHtml += html;
        hasNextPage = hasNext;
        stopReason = reason;

        if (stopReason === 'captcha') {
            pageCount--;
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

/**
 * [模式3] 执行妙手链接分页采集
 * @param {chrome.tabs.Tab} tab - 当前Tab
 * @param {number} maxPages - 用户设定的最大采集页数
 */
async function runMiaoshouScrape(tab, maxPages) {
    let allData = [];
    let pageCount = 0;
    let hasNextPage = true;
    let stopReason = "unknown";

    while (hasNextPage && pageCount < maxPages) {
        pageCount++;
        setStatus(`妙手采集中... 第 ${pageCount} / ${maxPages === 999 ? '?' : maxPages} 页...`, 'info');

        // 关键点：等待页面渲染完毕 (妙手页面翻页后有明显的加载时间)
        await new Promise(resolve => setTimeout(resolve, 2000));


        const results = await chrome.scripting.executeScript({
            target: { tabId: tab.id },
            func: scrapeMiaoshouPageAndAdvance,
            args: [SELECTORS.miaoshou]
        });

        const { data, hasNext, stopReason: reason, error } = results[0].result;
        if (error) throw new Error(error);

        allData = allData.concat(data);
        hasNextPage = hasNext;
        stopReason = reason;

        if (stopReason === 'endOfPages') {
            break;
        }

        // 翻页后的稳定等待时间
        if (hasNextPage) {
            await new Promise(resolve => setTimeout(resolve, Math.random() * 1000 + 1500));
        }
    }

    if (stopReason !== 'endOfPages' && pageCount === maxPages) {
        stopReason = "maxPages";
    }

    return { data: allData, count: allData.length, pageCount, stopReason };
}


// --- 5. DOM 监听器 ---

document.addEventListener('DOMContentLoaded', () => {
    const scrapeButton = document.getElementById('scrapeButton');
    const pageLimitInput = document.getElementById('pageLimitInput');
    const categoryOptions = document.getElementById('categoryOptions');
    const modeCategory = document.getElementById('modeCategory');
    const modeRanking = document.getElementById('modeRanking');
    const modeMiaoshou = document.getElementById('modeMiaoshou');

    function updateModeUI() {
        // 只有 1688 类目采集 (category) 和 妙手采集 (miaoshou) 需要页数限制
        if (modeCategory.checked || modeMiaoshou.checked) {
            categoryOptions.style.display = 'block';
        } else {
            categoryOptions.style.display = 'none';
        }
    }
    modeCategory.addEventListener('change', updateModeUI);
    modeRanking.addEventListener('change', updateModeUI);
    modeMiaoshou.addEventListener('change', updateModeUI);
    updateModeUI();

    scrapeButton.addEventListener('click', async () => {
        scrapeButton.disabled = true;
        setStatus("准备中...", 'info');

        try {
            const selectedMode = document.querySelector('input[name="scrapeMode"]:checked').value;
            let tabsQuery;

            if (selectedMode === 'miaoshou') {
                tabsQuery = {
                    active: true,
                    currentWindow: true,
                    url: "https://erp.91miaoshou.com/*"
                };
            } else {
                tabsQuery = {
                    active: true,
                    currentWindow: true,
                    url: "https://*.1688.com/*"
                };
            }

            const [tab] = await chrome.tabs.query(tabsQuery);

            if (!tab) {
                const requiredSite = selectedMode === 'miaoshou' ? "妙手的跳过链接页面" : "一个1688的页面";
                throw new Error(`请先打开${requiredSite}。`);
            }

            // --- 核心采集逻辑分支 ---
            if (selectedMode === 'category') {
                let maxPages = parseInt(pageLimitInput.value, 10);
                if (isNaN(maxPages) || maxPages < 1) {
                    maxPages = 999;
                }
                const result = await runCategoryScrape(tab, maxPages);
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

                if (stopReason === 'captcha') {
                    setStatus(`采集 ${pageCount} 页后遇验证码停止。已下载。`, 'warning');
                } else if (stopReason === 'maxPages') {
                    setStatus(`已达 ${pageCount} 页上限。已下载。`, 'success');
                } else {
                    setStatus(`已采集 ${pageCount} 页！已下载。`, 'success');
                }

            } else if (selectedMode === 'ranking') {
                const result = await runRankingScrape(tab);
                const { allHtml, stopReason } = result;

                if (!allHtml || allHtml.trim() === "") {
                    throw new Error("采集到了0个商品，请检查选择器。");
                }

                downloadHtml(allHtml, selectedMode, 1);

                if (stopReason === 'captcha') {
                    setStatus(`滚动中遇验证码停止。已下载(可能不全)。`, 'warning');
                } else {
                    setStatus(`榜单采集完毕！已下载。`, 'success');
                }
            } else if (selectedMode === 'miaoshou') {
                // *** 妙手采集 (分页模式) ***
                let maxPages = parseInt(pageLimitInput.value, 10);
                if (isNaN(maxPages) || maxPages < 1) {
                    maxPages = 999;
                }

                const result = await runMiaoshouScrape(tab, maxPages);
                const { data, count, pageCount, stopReason } = result;

                if (count === 0) {
                    throw new Error("妙手采集到0条数据，请检查选择器或页面是否正确。");
                }

                downloadCsv(data);

                if (stopReason === 'maxPages') {
                    setStatus(`妙手采集完毕！已达 ${pageCount} 页上限，共收集 ${count} 条数据，已下载 CSV 文件。`, 'success');
                } else if (stopReason === 'endOfPages') {
                    setStatus(`妙手采集完毕！已到达末页 (${pageCount} 页)，共收集 ${count} 条数据，已下载 CSV 文件。`, 'success');
                } else {
                    setStatus(`妙手采集完成。共收集 ${count} 条数据，已下载 CSV 文件。`, 'success');
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