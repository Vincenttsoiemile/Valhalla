// API 基礎 URL
const API_BASE = window.location.origin;

// 全域變數
let map;
let map2;
let startMarker = null;
let endMarker = null;
let orderMarkers = [];
let orderMarkers2 = [];
let routePolyline = null;
let currentOrders = [];
let isSettingEndPoint = false;

// 智能建議相關
let currentAnalysis = null;
let visualizationLayers = [];

// 路線導航相關
let navigationMode = false;
let currentRouteIndex = 0;
let routeSegments = [];
let currentSegmentPolyline = null;
let highlightMarkers = [];

// 所有路線段數據
let allRouteSegments = [];
let allRoutePolylines = [];
let highlightedPolylines = [];

// 地圖同步標記（防止無限循環）
let isSyncing = false;

// 初始化地圖
function initMap() {
    // 多倫多座標
    map = L.map('map').setView([43.6532, -79.3832], 11);
    
    // OpenStreetMap 圖層
    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
        attribution: '© OpenStreetMap contributors',
        maxZoom: 19
    }).addTo(map);
    
    // 點擊地圖設置起點或終點
    map.on('click', function(e) {
        if (isSettingEndPoint) {
            setEndPoint(e.latlng.lat, e.latlng.lng);
            isSettingEndPoint = false;
            document.getElementById('setEndPointBtn').textContent = '點擊地圖設置終點';
        } else {
            setStartPoint(e.latlng.lat, e.latlng.lng);
        }
    });
    
    // 地圖1 移動時同步地圖2
    map.on('moveend', function() {
        if (!isSyncing && map2) {
            isSyncing = true;
            map2.setView(map.getCenter(), map.getZoom(), { animate: false });
            setTimeout(() => { isSyncing = false; }, 100);
        }
    });
    
    // 地圖1 縮放時同步地圖2
    map.on('zoomend', function() {
        if (!isSyncing && map2) {
            isSyncing = true;
            map2.setZoom(map.getZoom(), { animate: false });
            setTimeout(() => { isSyncing = false; }, 100);
        }
    });
    
    // 強制重新計算地圖大小
    setTimeout(() => {
        map.invalidateSize();
    }, 100);
}

// 初始化第二個地圖
function initMap2() {
    map2 = L.map('map2').setView([43.6532, -79.3832], 11);
    
    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
        attribution: '© OpenStreetMap contributors',
        maxZoom: 19
    }).addTo(map2);
    
    // 地圖2 移動時同步地圖1
    map2.on('moveend', function() {
        if (!isSyncing && map) {
            isSyncing = true;
            map.setView(map2.getCenter(), map2.getZoom(), { animate: false });
            setTimeout(() => { isSyncing = false; }, 100);
        }
    });
    
    // 地圖2 縮放時同步地圖1
    map2.on('zoomend', function() {
        if (!isSyncing && map) {
            isSyncing = true;
            map.setZoom(map2.getZoom(), { animate: false });
            setTimeout(() => { isSyncing = false; }, 100);
        }
    });
    
    // 強制重新計算地圖大小
    setTimeout(() => {
        map2.invalidateSize();
    }, 100);
}

// 設置起點
function setStartPoint(lat, lon) {
    document.getElementById('startLat').value = lat.toFixed(6);
    document.getElementById('startLon').value = lon.toFixed(6);
    
    // 移除舊標記
    if (startMarker) {
        map.removeLayer(startMarker);
    }
    
    // 建立起點標記（綠色）
    const greenIcon = L.icon({
        iconUrl: 'https://raw.githubusercontent.com/pointhi/leaflet-color-markers/master/img/marker-icon-2x-green.png',
        shadowUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/images/marker-shadow.png',
        iconSize: [25, 41],
        iconAnchor: [12, 41],
        popupAnchor: [1, -34],
        shadowSize: [41, 41]
    });
    
    startMarker = L.marker([lat, lon], { icon: greenIcon })
        .addTo(map)
        .bindPopup('<div class="popup-title">起點</div>')
        .openPopup();
    
    // 啟用計算按鈕
    updateCalculateButton();
}

// 設置終點
function setEndPoint(lat, lon) {
    document.getElementById('endLat').value = lat.toFixed(6);
    document.getElementById('endLon').value = lon.toFixed(6);
    
    // 移除舊標記
    if (endMarker) {
        map.removeLayer(endMarker);
    }
    
    // 建立終點標記（紅色）
    const redIcon = L.icon({
        iconUrl: 'https://raw.githubusercontent.com/pointhi/leaflet-color-markers/master/img/marker-icon-2x-red.png',
        shadowUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/images/marker-shadow.png',
        iconSize: [25, 41],
        iconAnchor: [12, 41],
        popupAnchor: [1, -34],
        shadowSize: [41, 41]
    });
    
    endMarker = L.marker([lat, lon], { icon: redIcon })
        .addTo(map)
        .bindPopup('<div class="popup-title">終點</div>')
        .openPopup();
}

// 清除起點
document.getElementById('clearStartBtn').addEventListener('click', function() {
    document.getElementById('startLat').value = '';
    document.getElementById('startLon').value = '';
    
    if (startMarker) {
        map.removeLayer(startMarker);
        startMarker = null;
    }
    
    updateCalculateButton();
});

// 清除終點
document.getElementById('clearEndBtn').addEventListener('click', function() {
    document.getElementById('endLat').value = '';
    document.getElementById('endLon').value = '';
    
    if (endMarker) {
        map.removeLayer(endMarker);
        endMarker = null;
    }
});

// 點擊地圖設置終點按鈕
document.getElementById('setEndPointBtn').addEventListener('click', function() {
    isSettingEndPoint = true;
    this.textContent = '請點擊地圖...';
    alert('請在地圖上點擊以設置終點');
});

// 監聽起點輸入變化
document.getElementById('startLat').addEventListener('input', function() {
    const lat = parseFloat(this.value);
    const lon = parseFloat(document.getElementById('startLon').value);
    if (!isNaN(lat) && !isNaN(lon)) {
        setStartPoint(lat, lon);
    }
    updateCalculateButton();
});

document.getElementById('startLon').addEventListener('input', function() {
    const lat = parseFloat(document.getElementById('startLat').value);
    const lon = parseFloat(this.value);
    if (!isNaN(lat) && !isNaN(lon)) {
        setStartPoint(lat, lon);
    }
    updateCalculateButton();
});

// 監聽 order group 輸入變化
document.getElementById('orderGroupInput').addEventListener('input', updateCalculateButton);

// 計算路徑
document.getElementById('calculateBtn').addEventListener('click', async function() {
    const startLat = parseFloat(document.getElementById('startLat').value);
    const startLon = parseFloat(document.getElementById('startLon').value);
    const orderGroup = document.getElementById('orderGroupInput').value.trim();
    const optimizationMode = document.getElementById('optimizationMode').value;
    const sequenceMode = document.getElementById('sequenceMode').value;
    
    // 終點設置
    const endPointMode = document.querySelector('input[name="endPointMode"]:checked').value;
    const endLat = parseFloat(document.getElementById('endLat').value);
    const endLon = parseFloat(document.getElementById('endLon').value);
    
    // 分組模式參數
    const maxGroupSize = parseInt(document.getElementById('maxGroupSize').value) || 30;
    const clusterRadius = parseFloat(document.getElementById('clusterRadius').value) || 1.0;
    const minSamples = parseInt(document.getElementById('minSamples').value) || 3;
    const metric = document.getElementById('metric').value || 'euclidean';
    const groupOrderMethod = document.getElementById('groupOrderMethod').value || 'greedy';
    const innerOrderMethod = document.getElementById('innerOrderMethod').value || 'nearest';
    const randomState = document.getElementById('randomState').value ? parseInt(document.getElementById('randomState').value) : null;
    const nInit = parseInt(document.getElementById('nInit').value) || 10;
    
    // 全局優化參數
    const globalMethod = document.getElementById('globalMethod').value || 'ortools';
    
    // 障礙檢測參數
    const verification = document.getElementById('verification').value;
    const groupPenalty = parseFloat(document.getElementById('groupPenalty').value) || 2.0;
    const innerPenalty = parseFloat(document.getElementById('innerPenalty').value) || 1.5;
    const checkHighways = document.getElementById('checkHighways').checked;
    
    if (!startLat || !startLon) {
        alert('請先設置起點');
        return;
    }
    
    if (!orderGroup) {
        alert('請輸入 order group');
        return;
    }
    
    try {
        showLoading(true);
        
        let data1, data2;
        
        if (optimizationMode === 'clustering') {
            // 分組模式：調用現有的路徑 API
            const [response1, response2] = await Promise.all([
                // API 1: 分組優化路徑
                fetch(`${API_BASE}/api/route`, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({
                        start: { lat: startLat, lon: startLon },
                        order_group: orderGroup,
                        costing: 'auto',
                        max_orders: 5000,
                        max_group_size: maxGroupSize,
                        cluster_radius: clusterRadius,
                        min_samples: minSamples,
                        metric: metric,
                        group_order_method: groupOrderMethod,
                        inner_order_method: innerOrderMethod,
                        random_state: randomState,
                        n_init: nInit,
                        verification: verification,
                        group_penalty: groupPenalty,
                        inner_penalty: innerPenalty,
                        check_highways: checkHighways,
                        end_point_mode: endPointMode,
                        end_point: (endPointMode === 'manual' && !isNaN(endLat) && !isNaN(endLon)) ? { lat: endLat, lon: endLon } : null
                    })
                }),
                // API 2: Delivery Sequence 順序
                fetch(`${API_BASE}/api/orders-sequence?order_group=${encodeURIComponent(orderGroup)}`)
            ]);
            
            data1 = await response1.json();
            data2 = await response2.json();
            
            if (!response1.ok) {
                throw new Error(data1.error || '計算路徑失敗');
            }
            
            if (!response2.ok) {
                throw new Error(data2.error || '取得 delivery sequence 失敗');
            }
        } else {
            // 全局優化模式：調用新的全局 TSP API
            const [response1, response2] = await Promise.all([
                // API 1: 全局 TSP 優化
                fetch(`${API_BASE}/api/optimize-route-global`, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({
                        start: { lat: startLat, lon: startLon },
                        order_group: orderGroup,
                        method: globalMethod,
                        verification: verification,
                        penalty: innerPenalty,
                        check_highways: checkHighways,
                        end_point_mode: endPointMode,
                        end_point: (endPointMode === 'manual' && !isNaN(endLat) && !isNaN(endLon)) ? { lat: endLat, lon: endLon } : null
                    })
                }),
                // API 2: Delivery Sequence 順序
                fetch(`${API_BASE}/api/orders-sequence?order_group=${encodeURIComponent(orderGroup)}`)
            ]);
            
            data1 = await response1.json();
            data2 = await response2.json();
            
            if (!response1.ok) {
                throw new Error(data1.error || '全局優化失敗');
            }
            
            if (!response2.ok) {
                throw new Error(data2.error || '取得 delivery sequence 失敗');
            }
        }
        
        // 存儲當前配置和結果
        currentConfig = {
            startLat,
            startLon,
            orderGroup,
            optimizationMode,
            maxGroupSize,
            clusterRadius,
            minSamples,
            metric,
            groupOrderMethod,
            innerOrderMethod,
            globalMethod,
            randomState,
            nInit,
            verification,
            groupPenalty,
            innerPenalty,
            checkHighways,
            sequenceMode,
            endPointMode,
            endLat,
            endLon
        };
        currentResults = data1;
        
        // 顯示結果
        displayResults(data1, sequenceMode);
        
        // 在地圖1上繪製 Valhalla 路徑
        drawRoute(data1, sequenceMode);
        
        // 如果有手動終點，顯示在地圖上
        if (endPointMode === 'manual' && !isNaN(endLat) && !isNaN(endLon)) {
            setEndPoint(endLat, endLon);
        }
        
        // 在地圖2上顯示 Delivery Sequence 順序
        drawSequenceMap(data2);
        
        // 檢查是否啟用預加載
        const preloadEnabled = document.getElementById('preloadRoutes').checked;
        if (preloadEnabled) {
            console.log('開始預加載路線...');
            await preloadAllRoutes(data1, startLat, startLon);
            console.log('預加載完成！');
        } else {
            console.log('預加載已停用，跳過路線加載');
        }
        
        // 處理演算法步驟（如果有）
        if (data1.algorithm_steps && data1.algorithm_steps.length > 0) {
            console.log('演算法步驟數據:', data1.algorithm_steps);
            initAlgorithmViewer(data1.algorithm_steps, data1);
        }
        
        // 顯示完成提示
        showSuccessAlert();
        
    } catch (error) {
        alert(`錯誤: ${error.message}`);
    } finally {
        showLoading(false);
    }
});

// 顯示結果
function displayResults(data, sequenceMode) {
    // 顯示訂單列表
    const ordersList = document.getElementById('ordersList');
    ordersList.innerHTML = '';
    
    // 建立跨河訂單對的集合
    const crossingSet = new Set();
    if (data.crossings && data.crossings.length > 0) {
        data.crossings.forEach(crossing => {
            crossingSet.add(crossing.from);
            crossingSet.add(crossing.to);
        });
    }
    
    data.orders.forEach((order, index) => {
        const div = document.createElement('div');
        div.className = 'order-item';
        
        // 如果這個訂單涉及跨河，加上標記
        if (crossingSet.has(order.tracking_number)) {
            div.className += ' crossing-warning';
        }
        
        // 根據模式選擇顯示序號
        const displaySeq = sequenceMode === 'continuous' 
            ? order.sequence 
            : (order.group_sequence || `#${index + 1}`);
        
        div.innerHTML = `
            <span class="order-number">${displaySeq}</span>
            <span>${order.tracking_number}</span>
            ${crossingSet.has(order.tracking_number) ? '<span class="river-icon">🌊</span>' : ''}
        `;
        ordersList.appendChild(div);
    });
    
    // 顯示跨河檢測摘要
    if (data.verification_method !== 'none' && data.crossings) {
        const summary = document.createElement('div');
        summary.className = 'crossing-summary';
        summary.innerHTML = `
            <strong>跨河檢測結果:</strong> 發現 ${data.crossings.length} 處可能跨河
        `;
        ordersList.insertBefore(summary, ordersList.firstChild);
    }
    
    document.getElementById('resultsPanel').style.display = 'block';
}

// 繪製路徑
function drawRoute(data, sequenceMode) {
    // 清除舊路徑和標記
    if (routePolyline) {
        map.removeLayer(routePolyline);
        routePolyline = null;
    }
    clearOrderMarkers();
    // 清除地圖上的 polylines，但不清除數據
    clearAllRoutePolylines();
    
    // 在地圖上顯示訂單標記，帶有群組順序編號
    const groupColors = {
        'A': '#e74c3c', 'B': '#3498db', 'C': '#2ecc71', 'D': '#f39c12',
        'E': '#9b59b6', 'F': '#1abc9c', 'G': '#e67e22', 'H': '#34495e',
        'I': '#16a085', 'J': '#c0392b', 'K': '#d35400', 'L': '#8e44ad',
        'M': '#27ae60', 'N': '#2980b9', 'O': '#c0392b', 'P': '#16a085',
        'Q': '#d35400', 'R': '#2c3e50', 'S': '#f39c12', 'T': '#e74c3c',
        'U': '#9b59b6', 'V': '#3498db', 'W': '#2ecc71', 'X': '#e67e22',
        'Y': '#1abc9c', 'Z': '#34495e', 'End': '#dc3545', 'Global': '#3498db'
    };
    
    // 步驟 1: 檢測相同位置的訂單
    const locationGroups = {};
    data.orders.forEach((order, index) => {
        const key = `${order.lat.toFixed(6)},${order.lon.toFixed(6)}`;
        if (!locationGroups[key]) {
            locationGroups[key] = [];
        }
        locationGroups[key].push({ order, index });
    });
    
    // 步驟 2: 為每個訂單添加標記（相同位置自動偏移）
    data.orders.forEach((order, index) => {
        // 跳過終點標記（單獨處理）
        if (order.tracking_number === 'ENDPOINT') {
            // 顯示終點標記（紅色星形）
            const redIcon = L.icon({
                iconUrl: 'https://raw.githubusercontent.com/pointhi/leaflet-color-markers/master/img/marker-icon-2x-red.png',
                shadowUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/images/marker-shadow.png',
                iconSize: [25, 41],
                iconAnchor: [12, 41],
                popupAnchor: [1, -34],
                shadowSize: [41, 41]
            });
            
            const endMarkerTemp = L.marker([order.lat, order.lon], { icon: redIcon })
                .addTo(map)
                .bindPopup('<div class="popup-title">終點 (手動設置)</div>');
            
            orderMarkers.push(endMarkerTemp);
            return;
        }
        
        const key = `${order.lat.toFixed(6)},${order.lon.toFixed(6)}`;
        const ordersAtLocation = locationGroups[key];
        const isMultiple = ordersAtLocation.length > 1;
        
        // 根據模式選擇顯示序號和顏色
        let displaySeq, bgColor;
        
        if (sequenceMode === 'continuous') {
            // 連號模式：顯示全局序號，使用統一顏色
            displaySeq = order.sequence;
            bgColor = '#3498db';  // 統一藍色
        } else {
            // 不連號模式：顯示群組序號，按群組上色
            displaySeq = order.group_sequence || `${index + 1}`;
            const group = order.group || 'A';
            bgColor = groupColors[group] || '#dc3545';
        }
        
        // 如果同一位置有多個訂單，添加小量偏移（圓形排列）
        let lat = order.lat;
        let lon = order.lon;
        
        if (isMultiple) {
            const positionIndex = ordersAtLocation.findIndex(item => item.index === index);
            const angle = (positionIndex / ordersAtLocation.length) * 2 * Math.PI;
            const offset = 0.00008;  // 約 9米偏移
            lat += Math.cos(angle) * offset;
            lon += Math.sin(angle) * offset;
        }
        
        // 創建帶編號的自訂 div icon（如果多個訂單添加徽章）
        const badge = isMultiple ? '<span class="multi-badge">●</span>' : '';
        const numberIcon = L.divIcon({
            html: `<div class="number-marker" style="background: ${bgColor};">${displaySeq}${badge}</div>`,
            className: 'custom-div-icon',
            iconSize: [40, 40],
            iconAnchor: [20, 20],
            popupAnchor: [0, -20]
        });
        
        // 準備 Popup 內容
        let popupContent = `<div class="popup-title">${displaySeq}</div>`;
        popupContent += `<div class="popup-tracking">${order.tracking_number}</div>`;
        
        // 如果同一位置有多個訂單，顯示所有訂單
        if (isMultiple) {
            popupContent += `<div class="popup-multiple">📍 此位置共 ${ordersAtLocation.length} 個訂單：</div>`;
            ordersAtLocation.forEach(item => {
                const seq = sequenceMode === 'continuous' 
                    ? item.order.sequence 
                    : (item.order.group_sequence || `#${item.index + 1}`);
                popupContent += `<div class="popup-item">• ${seq}: ${item.order.tracking_number}</div>`;
            });
        }
        
        const marker = L.marker([lat, lon], { icon: numberIcon })
            .addTo(map)
            .bindPopup(popupContent);
        
        // 添加懸停事件
        marker.orderIndex = index;
        marker.on('mouseover', function() {
            highlightOrderRoutes(index);
        });
        marker.on('mouseout', function() {
            unhighlightOrderRoutes();
        });
        
        orderMarkers.push(marker);
    });
    
    // 調整視角包含所有訂單點和起點
    const bounds = L.latLngBounds(data.orders.map(o => [o.lat, o.lon]));
    if (startMarker) {
        bounds.extend(startMarker.getLatLng());
    }
    map.fitBounds(bounds, { padding: [50, 50] });
}

// 解碼 Valhalla polyline (precision 6)
function decodePolyline(encoded) {
    const coordinates = [];
    let index = 0;
    let lat = 0;
    let lon = 0;
    
    while (index < encoded.length) {
        let b;
        let shift = 0;
        let result = 0;
        
        do {
            b = encoded.charCodeAt(index++) - 63;
            result |= (b & 0x1f) << shift;
            shift += 5;
        } while (b >= 0x20);
        
        const dlat = ((result & 1) ? ~(result >> 1) : (result >> 1));
        lat += dlat;
        
        shift = 0;
        result = 0;
        
        do {
            b = encoded.charCodeAt(index++) - 63;
            result |= (b & 0x1f) << shift;
            shift += 5;
        } while (b >= 0x20);
        
        const dlon = ((result & 1) ? ~(result >> 1) : (result >> 1));
        lon += dlon;
        
        coordinates.push([lat / 1e6, lon / 1e6]);
    }
    
    return coordinates;
}

// 繪製地圖2：Delivery Sequence 順序
function drawSequenceMap(data) {
    // 清除舊標記
    clearOrderMarkers2();
    
    if (!data.orders || data.orders.length === 0) {
        return;
    }
    
    // 在地圖2上顯示訂單標記
    data.orders.forEach((order, index) => {
        const displaySeq = order.delivery_sequence_original || order.delivery_sequence;
        
        // 統一藍色
        const bgColor = '#3498db';
        
        // 創建帶編號的自訂 div icon
        const numberIcon = L.divIcon({
            html: `<div class="number-marker" style="background: ${bgColor};">${displaySeq}</div>`,
            className: 'custom-div-icon',
            iconSize: [40, 40],
            iconAnchor: [20, 20],
            popupAnchor: [0, -20]
        });
        
        // 準備 Popup 內容
        let popupContent = `<div class="popup-title">序號 ${displaySeq}</div>`;
        popupContent += `<div class="popup-tracking">${order.tracking_number}</div>`;
        
        const marker = L.marker([order.lat, order.lon], { icon: numberIcon })
            .addTo(map2)
            .bindPopup(popupContent);
        
        orderMarkers2.push(marker);
    });
    
    // 調整視角包含所有訂單點
    const bounds = L.latLngBounds(data.orders.map(o => [o.lat, o.lon]));
    map2.fitBounds(bounds, { padding: [50, 50] });
}

// 清除訂單標記
function clearOrderMarkers() {
    orderMarkers.forEach(marker => map.removeLayer(marker));
    orderMarkers = [];
}

// 清除地圖2的訂單標記
function clearOrderMarkers2() {
    orderMarkers2.forEach(marker => map2.removeLayer(marker));
    orderMarkers2 = [];
}

// 更新計算按鈕狀態
function updateCalculateButton() {
    const hasStart = document.getElementById('startLat').value && document.getElementById('startLon').value;
    const hasOrderGroup = document.getElementById('orderGroupInput').value.trim();
    
    document.getElementById('calculateBtn').disabled = !(hasStart && hasOrderGroup);
}

// 進度步驟管理
let progressInterval = null;
let currentStep = 0;

// 顯示/隱藏載入中（全屏版本）
function showLoading(show) {
    const fullScreenLoading = document.getElementById('fullScreenLoading');
    if (fullScreenLoading) {
        fullScreenLoading.style.display = show ? 'flex' : 'none';
    }
    // 舊版（備用）
    const oldLoadingPanel = document.getElementById('loadingPanel');
    if (oldLoadingPanel) {
        oldLoadingPanel.style.display = 'none';
    }
    
    if (show) {
        startProgressAnimation();
    } else {
        stopProgressAnimation();
    }
}

// 開始進度動畫
function startProgressAnimation() {
    currentStep = 0;
    
    // 重置所有步驟
    const steps = document.querySelectorAll('.step-item');
    steps.forEach(step => {
        step.classList.remove('active', 'completed');
        const icon = step.querySelector('.step-icon');
        icon.textContent = '⏳';
    });
    
    // 立即激活第一步
    updateStep(0, 'active');
    
    // 根據訂單數量估算時間
    const orderGroup = document.getElementById('orderGroupInput').value;
    const optimizationMode = document.getElementById('optimizationMode').value;
    
    // 估算每個步驟的時間（毫秒）
    let stepTimings = [
        500,   // 載入訂單資料
        2000,  // DBSCAN 聚類
        1000,  // 處理噪聲點
        1500,  // K-means 細分
        2000,  // 群組排序
        1500,  // 組內排序
        1000   // 跨河檢測
    ];
    
    // 如果是全局優化模式，調整時間
    if (optimizationMode === 'global') {
        stepTimings = [
            500,   // 載入訂單資料
            3000,  // 全局 TSP 優化（較長）
            0,     // 跳過
            0,     // 跳過
            0,     // 跳過
            0,     // 跳過
            1000   // 驗證
        ];
    }
    
    let totalTime = 0;
    progressInterval = [];
    
    stepTimings.forEach((timing, index) => {
        if (timing > 0) {
            totalTime += timing;
            const timer = setTimeout(() => {
                if (index > 0) {
                    updateStep(index - 1, 'completed');
                }
                updateStep(index, 'active');
            }, totalTime);
            progressInterval.push(timer);
        }
    });
}

// 停止進度動畫
function stopProgressAnimation() {
    if (progressInterval && progressInterval.length > 0) {
        progressInterval.forEach(timer => clearTimeout(timer));
        progressInterval = [];
    }
    
    // 標記所有步驟為完成
    const steps = document.querySelectorAll('.step-item');
    steps.forEach(step => {
        step.classList.remove('active');
        step.classList.add('completed');
        const icon = step.querySelector('.step-icon');
        icon.textContent = '✓';
    });
}

// 更新單個步驟狀態
function updateStep(stepIndex, status) {
    const steps = document.querySelectorAll('.step-item');
    if (stepIndex < steps.length) {
        const step = steps[stepIndex];
        const icon = step.querySelector('.step-icon');
        
        step.classList.remove('active', 'completed');
        
        if (status === 'active') {
            step.classList.add('active');
            icon.textContent = '⏳';
        } else if (status === 'completed') {
            step.classList.add('completed');
            icon.textContent = '✓';
        }
    }
}

// 顯示完成提示
function showSuccessAlert() {
    const alert = document.getElementById('successAlert');
    alert.style.display = 'flex';
    
    // 1 秒後自動隱藏
    setTimeout(() => {
        alert.style.display = 'none';
    }, 1000);
}

// 監聽驗證方式變化，顯示/隱藏懲罰係數設置
document.getElementById('verification').addEventListener('change', function() {
    const penaltySettings = document.getElementById('penaltySettings');
    const highwayOption = document.getElementById('highwayOption');

    if (this.value === 'geometry' || this.value === 'api') {
        penaltySettings.style.display = 'block';
        highwayOption.style.display = 'block';
    } else {
        penaltySettings.style.display = 'none';
        highwayOption.style.display = 'none';
    }
});

// 監聽懲罰係數變化，更新顯示值
document.getElementById('groupPenalty').addEventListener('input', function() {
    const display = this.nextElementSibling;
    display.textContent = `${parseFloat(this.value).toFixed(1)}x`;
});

document.getElementById('innerPenalty').addEventListener('input', function() {
    const display = this.nextElementSibling;
    display.textContent = `${parseFloat(this.value).toFixed(1)}x`;
});

// 存儲當前配置和結果
let currentConfig = null;
let currentResults = null;

// 生成分享連結
function generateShareLink() {
    if (!currentConfig) return '';
    
    const params = {
        startLat: currentConfig.startLat,
        startLon: currentConfig.startLon,
        orderGroup: currentConfig.orderGroup,
        maxGroupSize: currentConfig.maxGroupSize,
        clusterRadius: currentConfig.clusterRadius,
        minSamples: currentConfig.minSamples,
        metric: currentConfig.metric,
        randomState: currentConfig.randomState,
        nInit: currentConfig.nInit,
            verification: currentConfig.verification,
            groupPenalty: currentConfig.groupPenalty,
            innerPenalty: currentConfig.innerPenalty,
            checkHighways: currentConfig.checkHighways,
            sequenceMode: currentConfig.sequenceMode
    };
    
    const encoded = btoa(JSON.stringify(params));
    return `${window.location.origin}${window.location.pathname}?config=${encoded}`;
}

// 從 URL 載入配置
function loadConfigFromUrl() {
    const urlParams = new URLSearchParams(window.location.search);
    const configParam = urlParams.get('config');
    
    if (configParam) {
        try {
            const config = JSON.parse(atob(configParam));
            
            // 設置表單值
            if (config.startLat && config.startLon) {
                setStartPoint(config.startLat, config.startLon);
            }
            if (config.orderGroup) {
                document.getElementById('orderGroupInput').value = config.orderGroup;
            }
            if (config.maxGroupSize) {
                document.getElementById('maxGroupSize').value = config.maxGroupSize;
            }
            if (config.clusterRadius) {
                document.getElementById('clusterRadius').value = config.clusterRadius;
            }
            if (config.minSamples) {
                document.getElementById('minSamples').value = config.minSamples;
            }
            if (config.metric) {
                document.getElementById('metric').value = config.metric;
            }
            if (config.randomState !== undefined && config.randomState !== null) {
                document.getElementById('randomState').value = config.randomState;
            }
            if (config.nInit) {
                document.getElementById('nInit').value = config.nInit;
            }
            if (config.verification) {
                document.getElementById('verification').value = config.verification;
                // 觸發變化事件以顯示/隱藏懲罰係數
                document.getElementById('verification').dispatchEvent(new Event('change'));
            }
            if (config.groupPenalty) {
                document.getElementById('groupPenalty').value = config.groupPenalty;
                document.getElementById('groupPenalty').dispatchEvent(new Event('input'));
            }
            if (config.innerPenalty) {
                document.getElementById('innerPenalty').value = config.innerPenalty;
                document.getElementById('innerPenalty').dispatchEvent(new Event('input'));
            }
            if (config.checkHighways !== undefined) {
                document.getElementById('checkHighways').checked = config.checkHighways;
            }
            if (config.sequenceMode) {
                document.getElementById('sequenceMode').value = config.sequenceMode;
            }
            
            updateCalculateButton();
            
            // 顯示提示
            alert('已從分享連結載入配置！');
        } catch (e) {
            console.error('載入配置失敗:', e);
        }
    }
}

// PDF 導出功能已移除

// ========== 設定複製/導入功能 ==========

// 獲取當前所有設定
function getAllSettings() {
    const settings = {
        // 起點
        startLat: document.getElementById('startLat').value,
        startLon: document.getElementById('startLon').value,

        // 終點模式
        endPointMode: document.querySelector('input[name="endPointMode"]:checked')?.value,
        endLat: document.getElementById('endLat').value,
        endLon: document.getElementById('endLon').value,

        // Order Group
        orderGroup: document.getElementById('orderGroupInput').value,

        // 序號顯示模式
        sequenceMode: document.getElementById('sequenceMode').value,

        // 優化模式
        optimizationMode: document.getElementById('optimizationMode').value,
        globalMethod: document.getElementById('globalMethod').value,

        // 分組參數
        maxGroupSize: document.getElementById('maxGroupSize').value,
        clusterRadius: document.getElementById('clusterRadius').value,
        minSamples: document.getElementById('minSamples').value,
        metric: document.getElementById('metric').value,
        groupOrderMethod: document.getElementById('groupOrderMethod').value,
        innerOrderMethod: document.getElementById('innerOrderMethod').value,
        randomState: document.getElementById('randomState').value,
        nInit: document.getElementById('nInit').value,

        // 障礙檢測
        verification: document.getElementById('verification').value,
        checkHighways: document.getElementById('checkHighways').checked,
        groupPenalty: document.getElementById('groupPenalty').value,
        innerPenalty: document.getElementById('innerPenalty').value,

        // 路線預加載
        preloadRoutes: document.getElementById('preloadRoutes').checked
    };

    return settings;
}

// 複製設定到剪貼板
async function copySettingsToClipboard() {
    try {
        const settings = getAllSettings();
        const settingsText = JSON.stringify(settings, null, 2);

        await navigator.clipboard.writeText(settingsText);
        showNotification('✓ 設定已複製到剪貼板！', 'success');
        console.log('設定已複製:', settings);
    } catch (error) {
        console.error('複製設定失敗:', error);
        showNotification('✕ 複製失敗，請稍後再試', 'error');
    }
}

// 從剪貼板導入設定
async function importSettingsFromClipboard() {
    try {
        const clipboardText = await navigator.clipboard.readText();
        const settings = JSON.parse(clipboardText);

        // 應用設定
        applySettings(settings);

        showNotification('✓ 設定已成功導入！', 'success');
        console.log('設定已導入:', settings);
    } catch (error) {
        console.error('導入設定失敗:', error);
        showNotification('✕ 導入失敗，請確認剪貼板內容格式正確', 'error');
    }
}

// 應用設定到表單
function applySettings(settings) {
    // 起點
    if (settings.startLat && settings.startLon) {
        setStartPoint(parseFloat(settings.startLat), parseFloat(settings.startLon));
    }

    // 終點模式
    if (settings.endPointMode) {
        const radio = document.querySelector(`input[name="endPointMode"][value="${settings.endPointMode}"]`);
        if (radio) {
            radio.checked = true;
            radio.dispatchEvent(new Event('change'));
        }
    }

    if (settings.endLat && settings.endLon && settings.endPointMode === 'manual') {
        setEndPoint(parseFloat(settings.endLat), parseFloat(settings.endLon));
    }

    // Order Group
    if (settings.orderGroup) {
        document.getElementById('orderGroupInput').value = settings.orderGroup;
    }

    // 序號顯示模式
    if (settings.sequenceMode) {
        document.getElementById('sequenceMode').value = settings.sequenceMode;
    }

    // 優化模式
    if (settings.optimizationMode) {
        document.getElementById('optimizationMode').value = settings.optimizationMode;
        document.getElementById('optimizationMode').dispatchEvent(new Event('change'));
    }

    if (settings.globalMethod) {
        document.getElementById('globalMethod').value = settings.globalMethod;
    }

    // 分組參數
    if (settings.maxGroupSize) {
        document.getElementById('maxGroupSize').value = settings.maxGroupSize;
    }
    if (settings.clusterRadius) {
        document.getElementById('clusterRadius').value = settings.clusterRadius;
    }
    if (settings.minSamples) {
        document.getElementById('minSamples').value = settings.minSamples;
    }
    if (settings.metric) {
        document.getElementById('metric').value = settings.metric;
    }
    if (settings.groupOrderMethod) {
        document.getElementById('groupOrderMethod').value = settings.groupOrderMethod;
    }
    if (settings.innerOrderMethod) {
        document.getElementById('innerOrderMethod').value = settings.innerOrderMethod;
    }
    if (settings.randomState !== undefined && settings.randomState !== null && settings.randomState !== '') {
        document.getElementById('randomState').value = settings.randomState;
    }
    if (settings.nInit) {
        document.getElementById('nInit').value = settings.nInit;
    }

    // 障礙檢測
    if (settings.verification) {
        document.getElementById('verification').value = settings.verification;
        document.getElementById('verification').dispatchEvent(new Event('change'));
    }
    if (settings.checkHighways !== undefined) {
        document.getElementById('checkHighways').checked = settings.checkHighways;
    }
    if (settings.groupPenalty) {
        document.getElementById('groupPenalty').value = settings.groupPenalty;
        document.getElementById('groupPenalty').dispatchEvent(new Event('input'));
    }
    if (settings.innerPenalty) {
        document.getElementById('innerPenalty').value = settings.innerPenalty;
        document.getElementById('innerPenalty').dispatchEvent(new Event('input'));
    }

    // 路線預加載
    if (settings.preloadRoutes !== undefined) {
        document.getElementById('preloadRoutes').checked = settings.preloadRoutes;
    }

    updateCalculateButton();
}

// 顯示通知訊息
function showNotification(message, type = 'success') {
    // 創建通知元素
    const notification = document.createElement('div');
    notification.className = `settings-notification ${type}`;
    notification.textContent = message;

    // 添加到 body
    document.body.appendChild(notification);

    // 延遲顯示（觸發動畫）
    setTimeout(() => {
        notification.classList.add('show');
    }, 10);

    // 2 秒後移除
    setTimeout(() => {
        notification.classList.remove('show');
        setTimeout(() => {
            document.body.removeChild(notification);
        }, 300);
    }, 2000);
}

// ========== 路線導航功能 ==========

// 顯示路線導航器
function showRouteNavigator() {
    const navigator = document.getElementById('routeNavigator');
    navigator.classList.add('active');
    navigationMode = true;
    currentRouteIndex = 0;
    updateNavigationUI();
}

// 隱藏路線導航器
function hideRouteNavigator() {
    const navigator = document.getElementById('routeNavigator');
    navigator.classList.remove('active');
    navigationMode = false;
    clearRouteSegment();
}

// 清除當前路線段
function clearRouteSegment() {
    if (currentSegmentPolyline) {
        map.removeLayer(currentSegmentPolyline);
        currentSegmentPolyline = null;
    }
    
    // 清除高亮標記
    highlightMarkers.forEach(marker => map.removeLayer(marker));
    highlightMarkers = [];
}

// 更新導航 UI
function updateNavigationUI() {
    const progressText = document.getElementById('navProgressText');
    const progressFill = document.getElementById('navProgressFill');
    const prevBtn = document.getElementById('navPrevBtn');
    const nextBtn = document.getElementById('navNextBtn');
    
    if (!currentResults || !currentResults.orders) return;
    
    const totalSegments = currentResults.orders.length; // 包含起點到第一個訂單
    const progress = ((currentRouteIndex) / totalSegments) * 100;
    
    // 更新進度條
    progressFill.style.width = `${progress}%`;
    
    // 更新文字
    if (currentRouteIndex === 0) {
        const firstOrder = currentResults.orders[0];
        const displaySeq = currentConfig.sequenceMode === 'continuous' 
            ? firstOrder.sequence 
            : firstOrder.group_sequence;
        progressText.textContent = `起點 → ${displaySeq}`;
    } else {
        const fromOrder = currentResults.orders[currentRouteIndex - 1];
        const toOrder = currentResults.orders[currentRouteIndex];
        const fromSeq = currentConfig.sequenceMode === 'continuous' 
            ? fromOrder.sequence 
            : fromOrder.group_sequence;
        const toSeq = currentConfig.sequenceMode === 'continuous' 
            ? toOrder.sequence 
            : toOrder.group_sequence;
        progressText.textContent = `${fromSeq} → ${toSeq}`;
    }
    
    // 更新按鈕狀態
    prevBtn.disabled = currentRouteIndex === 0;
    nextBtn.disabled = currentRouteIndex >= totalSegments;
}

// 獲取兩點間的路線（通過後端代理避免 CORS，支持限流重試）
async function fetchRouteSegment(fromLat, fromLon, toLat, toLon, retryCount = 0) {
    const maxRetries = 3; // 最多重試 3 次
    
    try {
        const response = await fetch(`${API_BASE}/api/valhalla-route`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                locations: [
                    { lat: fromLat, lon: fromLon },
                    { lat: toLat, lon: toLon }
                ],
                costing: 'auto',
                directions_options: {
                    units: 'kilometers'
                }
            })
        });
        
        // 檢查是否是 429 限流錯誤
        if (response.status === 429) {
            if (retryCount < maxRetries) {
                const delay = 1500; // 增加延遲到 1.5 秒
                console.log(`API 限流，等待 ${delay/1000} 秒後重試 (${retryCount + 1}/${maxRetries})...`);
                await new Promise(resolve => setTimeout(resolve, delay));
                return fetchRouteSegment(fromLat, fromLon, toLat, toLon, retryCount + 1);
            } else {
                console.warn(`API 限流，已達最大重試次數 (${maxRetries})`);
                return null;
            }
        }
        
        const data = await response.json();
        
        if (data.trip && data.trip.legs && data.trip.legs.length > 0) {
            return data.trip.legs[0].shape;
        }
        
        return null;
    } catch (error) {
        console.error('獲取路線失敗:', error);
        return null;
    }
}

// 顯示路線段（從緩存讀取）
function showRouteSegment(index) {
    if (!currentResults || !currentResults.orders) return;
    if (index >= allRouteSegments.length) return;
    
    clearRouteSegment();
    
    const orders = currentResults.orders;
    const segment = allRouteSegments[index];
    
    // 從緩存繪製路線
    currentSegmentPolyline = L.polyline(segment.coords, {
        color: '#FF6B00',
        weight: 6,
        opacity: 1.0,
        dashArray: segment.isStraight ? '10, 10' : null
    }).addTo(map);
    
    // 調整視角
    map.fitBounds(currentSegmentPolyline.getBounds(), { padding: [80, 80] });
    
    // 獲取訂單信息
    let toOrder;
    if (index === 0) {
        toOrder = orders[0];
    } else {
        toOrder = orders[index];
    }
    
    const startLat = currentConfig.startLat;
    const startLon = currentConfig.startLon;
    
    // 添加高亮標記（起點或終點）
    if (index === 0) {
        // 高亮起點（綠色）
        const greenIcon = L.icon({
            iconUrl: 'https://raw.githubusercontent.com/pointhi/leaflet-color-markers/master/img/marker-icon-2x-green.png',
            shadowUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/images/marker-shadow.png',
            iconSize: [38, 61],
            iconAnchor: [19, 61],
            popupAnchor: [1, -54],
            shadowSize: [61, 61]
        });
        const startHighlight = L.marker([startLat, startLon], { icon: greenIcon })
            .addTo(map)
            .bindPopup('<div class="popup-title">起點</div>');
        highlightMarkers.push(startHighlight);
    }
    
    // 高亮目標訂單（黃色）
    const yellowIcon = L.icon({
        iconUrl: 'https://raw.githubusercontent.com/pointhi/leaflet-color-markers/master/img/marker-icon-2x-yellow.png',
        shadowUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/images/marker-shadow.png',
        iconSize: [38, 61],
        iconAnchor: [19, 61],
        popupAnchor: [1, -54],
        shadowSize: [61, 61]
    });
    
    const displaySeq = currentConfig.sequenceMode === 'continuous' 
        ? toOrder.sequence 
        : toOrder.group_sequence;
    
    const toHighlight = L.marker([toOrder.lat, toOrder.lon], { icon: yellowIcon })
        .addTo(map)
        .bindPopup(`<div class="popup-title">${displaySeq}</div><div class="popup-tracking">${toOrder.tracking_number}</div>`)
        .openPopup();
    highlightMarkers.push(toHighlight);
}

// Previous 按鈕
document.getElementById('navPrevBtn').addEventListener('click', function() {
    if (currentRouteIndex > 0) {
        currentRouteIndex--;
        showRouteSegment(currentRouteIndex);
        updateNavigationUI();
    }
});

// Next 按鈕（無需 async，從緩存讀取）
document.getElementById('navNextBtn').addEventListener('click', function() {
    if (currentResults && currentRouteIndex < currentResults.orders.length) {
        showRouteSegment(currentRouteIndex);
        currentRouteIndex++;
        updateNavigationUI();
    }
});

// Reset 按鈕
document.getElementById('navResetBtn').addEventListener('click', function() {
    hideRouteNavigator();
    currentRouteIndex = 0;
    
    // 重新顯示完整路徑
    if (currentResults) {
        const sequenceMode = currentConfig.sequenceMode || 'grouped';
        drawRoute(currentResults, sequenceMode);
    }
});

// ========== 預加載所有路線 ==========

// 清除所有路線 polylines（但保留 segments 數據）
function clearAllRoutePolylines() {
    allRoutePolylines.forEach(polyline => {
        if (map.hasLayer(polyline)) {
            map.removeLayer(polyline);
        }
    });
    allRoutePolylines = [];
    // 不要清空 allRouteSegments - 那是預加載的數據
}

// 高亮訂單的進入和離開路線
function highlightOrderRoutes(orderIndex) {
    if (!allRoutePolylines.length) return;
    
    // 清除之前的高亮
    unhighlightOrderRoutes();
    
    // 進入路線：前一個 → 這個訂單
    if (orderIndex < allRoutePolylines.length) {
        const enterPolyline = allRoutePolylines[orderIndex];
        if (enterPolyline) {
            enterPolyline.setStyle({
                color: '#2ecc71',
                weight: 6,
                opacity: 1.0
            });
            highlightedPolylines.push(enterPolyline);
        }
    }
    
    // 離開路線：這個訂單 → 下一個訂單
    if (orderIndex + 1 < allRoutePolylines.length) {
        const exitPolyline = allRoutePolylines[orderIndex + 1];
        if (exitPolyline) {
            exitPolyline.setStyle({
                color: '#3498db',
                weight: 6,
                opacity: 1.0
            });
            highlightedPolylines.push(exitPolyline);
        }
    }
}

// 取消高亮
function unhighlightOrderRoutes() {
    highlightedPolylines.forEach(polyline => {
        polyline.setStyle({
            color: '#7f8c8d',
            weight: 4,
            opacity: 0.6
        });
    });
    highlightedPolylines = [];
}

// 顯示/隱藏路線預加載視窗
function showRouteLoadingModal() {
    document.getElementById('routeLoadingModal').style.display = 'flex';
}

function hideRouteLoadingModal() {
    document.getElementById('routeLoadingModal').style.display = 'none';
}

// 更新路線預加載進度
function updateRouteLoadingProgress(current, total, actualCount, straightCount) {
    const progressText = document.getElementById('loadingProgressText');
    const progressBar = document.getElementById('loadingProgressBar');
    const actualRoutes = document.getElementById('actualRoutes');
    const straightRoutes = document.getElementById('straightRoutes');
    
    const percentage = (current / total) * 100;
    
    progressText.textContent = `載入路線 ${current}/${total} (${percentage.toFixed(0)}%)`;
    progressBar.style.width = `${percentage}%`;
    actualRoutes.textContent = actualCount;
    straightRoutes.textContent = straightCount;
}

// 預加載所有路線段（並行版本）
async function preloadAllRoutes(data, startLat, startLon) {
    if (!data.orders || data.orders.length === 0) {
        return;
    }
    
    const orders = data.orders;
    const totalSegments = orders.length;
    
    // 顯示進度視窗
    showRouteLoadingModal();
    updateRouteLoadingProgress(0, totalSegments, 0, 0);
    
    // 清空舊數據重新開始
    allRouteSegments = [];
    allRoutePolylines = [];
    let actualCount = 0;
    let straightCount = 0;
    
    // 準備所有路線段的請求參數
    const segmentRequests = [];
    for (let i = 0; i < totalSegments; i++) {
        let fromLat, fromLon, toLat, toLon;
        
        if (i === 0) {
            fromLat = startLat;
            fromLon = startLon;
            toLat = orders[0].lat;
            toLon = orders[0].lon;
        } else {
            fromLat = orders[i - 1].lat;
            fromLon = orders[i - 1].lon;
            toLat = orders[i].lat;
            toLon = orders[i].lon;
        }
        
        segmentRequests.push({
            index: i,
            fromLat,
            fromLon,
            toLat,
            toLon
        });
    }
    
    try {
        // 小批次並行處理（每批 3 個請求，符合 API 限制：1 req/sec）
        const batchSize = 3;
        const batches = [];
        for (let i = 0; i < segmentRequests.length; i += batchSize) {
            batches.push(segmentRequests.slice(i, i + batchSize));
        }
        
        let processedCount = 0;
        
        // 逐批處理
        for (const batch of batches) {
            // 並行獲取這批路線
            const batchPromises = batch.map(async (seg) => {
                const shape = await fetchRouteSegment(seg.fromLat, seg.fromLon, seg.toLat, seg.toLon);
                return { seg, shape };
            });
            
            // 等待這批完成
            const results = await Promise.allSettled(batchPromises);
            
            // 收集失敗的請求（需要串行重試）
            const failedSegments = [];
            
            // 處理成功的結果
            results.forEach(result => {
                if (result.status === 'fulfilled') {
                    const { seg, shape } = result.value;
                    
                    if (shape) {
                        const coords = decodePolyline(shape);
                        allRouteSegments[seg.index] = {
                            index: seg.index,
                            coords: coords,
                            from: { lat: seg.fromLat, lon: seg.fromLon },
                            to: { lat: seg.toLat, lon: seg.toLon },
                            isStraight: false
                        };
                        actualCount++;
                    } else {
                        // 第一次失敗，加入重試列表
                        failedSegments.push(seg);
                    }
                }
            });
            
            // 串行重試失敗的請求（一個一個來，避免限流）
            if (failedSegments.length > 0) {
                console.log(`${failedSegments.length} 個請求失敗，開始串行重試...`);
                
                for (const seg of failedSegments) {
                    // 等待 2 秒再重試（保守一點）
                    await new Promise(resolve => setTimeout(resolve, 2000));
                    
                    const shape = await fetchRouteSegment(seg.fromLat, seg.fromLon, seg.toLat, seg.toLon);
                    
                    if (shape) {
                        const coords = decodePolyline(shape);
                        allRouteSegments[seg.index] = {
                            index: seg.index,
                            coords: coords,
                            from: { lat: seg.fromLat, lon: seg.fromLon },
                            to: { lat: seg.toLat, lon: seg.toLon },
                            isStraight: false
                        };
                        actualCount++;
                        console.log(`✓ 串行重試成功: 路線 ${seg.index}`);
                    } else {
                        // 串行重試也失敗，使用直線
                        allRouteSegments[seg.index] = {
                            index: seg.index,
                            coords: [[seg.fromLat, seg.fromLon], [seg.toLat, seg.toLon]],
                            from: { lat: seg.fromLat, lon: seg.fromLon },
                            to: { lat: seg.toLat, lon: seg.toLon },
                            isStraight: true
                        };
                        straightCount++;
                        console.log(`✗ 串行重試失敗: 路線 ${seg.index}，使用直線`);
                    }
                    
                    // 更新進度
                    updateRouteLoadingProgress(processedCount, totalSegments, actualCount, straightCount);
                }
            }
            
            // 更新進度
            processedCount += batch.length;
            updateRouteLoadingProgress(processedCount, totalSegments, actualCount, straightCount);
            
            // 批次間延遲（3 秒，符合 API 限制：1 req/sec）
            if (processedCount < totalSegments) {
                await new Promise(resolve => setTimeout(resolve, 3000));
            }
        }
        
        // 繪製所有路線（灰色，半透明）
        const progressText = document.getElementById('loadingProgressText');
        progressText.textContent = '繪製路線到地圖...';
        await new Promise(resolve => setTimeout(resolve, 500));
        
        drawAllRoutes();
        
        // 顯示完成
        progressText.textContent = '✓ 載入完成！';
        await new Promise(resolve => setTimeout(resolve, 1000));
        
    } catch (error) {
        console.error('預加載路線失敗:', error);
        const progressText = document.getElementById('loadingProgressText');
        progressText.textContent = '❌ 載入失敗';
        await new Promise(resolve => setTimeout(resolve, 2000));
    } finally {
        hideRouteLoadingModal();
    }
}

// 繪製所有路線
function drawAllRoutes() {
    // 清除舊的
    clearAllRoutePolylines();
    
    console.log(`繪製 ${allRouteSegments.length} 條路線到地圖 1`);
    
    allRouteSegments.forEach(segment => {
        const polyline = L.polyline(segment.coords, {
            color: '#7f8c8d',  // 深灰色
            weight: 4,         // 加粗
            opacity: 0.6,      // 提高透明度到 60%
            dashArray: segment.isStraight ? '10, 10' : null
        }).addTo(map);
        
        allRoutePolylines.push(polyline);
    });
    
    console.log(`✓ 已繪製 ${allRoutePolylines.length} 條路線（灰色，60% 透明度）`);
}

// 修改 displayResults 函數，在計算完成後顯示導航器
const originalDisplayResults = displayResults;
displayResults = function(data, sequenceMode) {
    originalDisplayResults(data, sequenceMode);
    
    // 只有啟用預加載時才顯示導航器
    const preloadEnabled = document.getElementById('preloadRoutes').checked;
    if (preloadEnabled && allRouteSegments.length > 0) {
        showRouteNavigator();
    }
};

// ========== 智能建議功能 ==========

// 分析訂單分佈按鈕
document.getElementById('analyzeBtn').addEventListener('click', async function() {
    const orderGroup = document.getElementById('orderGroupInput').value.trim();
    
    if (!orderGroup) {
        alert('請先輸入 order group');
        return;
    }
    
    try {
        showLoading(true);
        
        const response = await fetch(`${API_BASE}/api/analyze-distribution`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                order_group: orderGroup
            })
        });
        
        const data = await response.json();
        
        if (!response.ok) {
            throw new Error(data.error || '分析失敗');
        }
        
        // 儲存分析結果
        currentAnalysis = data;
        
        // 顯示建議面板
        displaySuggestions(data);
        
        // 視覺化分佈特徵
        visualizeDistribution(data);
        
    } catch (error) {
        alert(`錯誤: ${error.message}`);
    } finally {
        showLoading(false);
    }
});

// 顯示建議面板
function displaySuggestions(data) {
    const panel = document.getElementById('suggestionPanel');
    
    // 更新統計資料
    document.getElementById('statTotalOrders').textContent = data.total_orders;
    document.getElementById('statAspectRatio').textContent = data.aspect_ratio;
    document.getElementById('statDensity').textContent = `${data.density} 訂單/km²`;
    document.getElementById('statOrientation').textContent = data.orientation === 'east-west' ? '東西向' : '南北向';
    
    // 更新分析結果
    document.getElementById('reasoningText').textContent = data.reasoning;
    
    // 更新建議值
    const suggestions = data.suggestions;
    
    // 群組排序方法
    const methodNames = {
        'greedy': 'Greedy（貪心）',
        'sweep': 'Sweep（極角）',
        '2opt': '2-opt（最優）'
    };
    document.getElementById('suggestGroupMethodValue').textContent = methodNames[suggestions.group_order_method] || suggestions.group_order_method;
    
    // 其他建議
    document.getElementById('suggestMaxGroupSizeValue').textContent = suggestions.max_group_size;
    document.getElementById('suggestClusterRadiusValue').textContent = suggestions.cluster_radius;
    document.getElementById('suggestMinSamplesValue').textContent = suggestions.min_samples;
    
    // 障礙檢測
    const verificationNames = {
        'none': '不檢測',
        'geometry': '幾何數據',
        'api': '實際路線'
    };
    document.getElementById('suggestVerificationValue').textContent = verificationNames[suggestions.verification] || suggestions.verification;
    
    // 如果建議啟用障礙檢測，顯示懲罰係數
    if (suggestions.verification !== 'none') {
        document.getElementById('penaltySuggestions').style.display = 'block';
        document.getElementById('suggestGroupPenaltyValue').textContent = suggestions.group_penalty;
        document.getElementById('suggestInnerPenaltyValue').textContent = suggestions.inner_penalty;
        document.getElementById('suggestCheckHighwaysValue').textContent = suggestions.check_highways ? '是' : '否';
    } else {
        document.getElementById('penaltySuggestions').style.display = 'none';
    }
    
    // 顯示面板
    panel.style.display = 'block';
    
    // 滾動到面板
    panel.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
}

// 視覺化分佈特徵
function visualizeDistribution(data) {
    // 清除舊的視覺化圖層
    clearVisualizationLayers();
    
    const viz = data.visualization;
    
    // 1. 繪製凸包
    if (viz.convex_hull && viz.convex_hull.length > 0) {
        const hullPolygon = L.polygon(viz.convex_hull, {
            color: '#3498db',
            weight: 2,
            fillColor: '#3498db',
            fillOpacity: 0.1,
            dashArray: '5, 5'
        }).addTo(map);
        
        hullPolygon.bindPopup(`<strong>訂單分佈範圍</strong><br>面積: ${data.hull_area_km} km²`);
        visualizationLayers.push(hullPolygon);
    }
    
    // 2. 繪製主軸
    if (viz.principal_axis) {
        const axisLine = L.polyline([
            viz.principal_axis.start,
            viz.principal_axis.end
        ], {
            color: '#e74c3c',
            weight: 3,
            dashArray: '10, 10'
        }).addTo(map);
        
        axisLine.bindPopup(`<strong>主軸方向</strong><br>角度: ${viz.principal_axis.angle}°<br>方向: ${data.orientation === 'east-west' ? '東西向' : '南北向'}`);
        visualizationLayers.push(axisLine);
    }
    
    // 3. 標記中心點
    if (viz.center) {
        const centerMarker = L.circleMarker(viz.center, {
            radius: 8,
            color: '#f39c12',
            fillColor: '#f39c12',
            fillOpacity: 0.8,
            weight: 2
        }).addTo(map);
        
        centerMarker.bindPopup(`<strong>分佈中心</strong><br>長寬比: ${data.aspect_ratio}<br>密度: ${data.density} 訂單/km²`);
        visualizationLayers.push(centerMarker);
    }
    
    // 調整地圖視角包含所有視覺化元素
    if (visualizationLayers.length > 0) {
        const group = L.featureGroup(visualizationLayers);
        map.fitBounds(group.getBounds(), { padding: [50, 50] });
    }
}

// 清除視覺化圖層
function clearVisualizationLayers() {
    visualizationLayers.forEach(layer => {
        if (map.hasLayer(layer)) {
            map.removeLayer(layer);
        }
    });
    visualizationLayers = [];
}

// 應用建議按鈕
document.getElementById('applySuggestionsBtn').addEventListener('click', function() {
    if (!currentAnalysis) return;
    
    const suggestions = currentAnalysis.suggestions;
    
    // 根據勾選狀態應用建議
    if (document.getElementById('suggestGroupMethod').checked) {
        document.getElementById('groupOrderMethod').value = suggestions.group_order_method;
    }
    
    if (document.getElementById('suggestMaxGroupSize').checked) {
        document.getElementById('maxGroupSize').value = suggestions.max_group_size;
    }
    
    if (document.getElementById('suggestClusterRadius').checked) {
        document.getElementById('clusterRadius').value = suggestions.cluster_radius;
    }
    
    if (document.getElementById('suggestMinSamples').checked) {
        document.getElementById('minSamples').value = suggestions.min_samples;
    }
    
    if (document.getElementById('suggestVerification').checked) {
        document.getElementById('verification').value = suggestions.verification;
        // 觸發變化事件以顯示/隱藏懲罰係數
        document.getElementById('verification').dispatchEvent(new Event('change'));
        
        // 應用懲罰係數
        if (suggestions.verification !== 'none') {
            if (document.getElementById('suggestGroupPenalty').checked) {
                document.getElementById('groupPenalty').value = suggestions.group_penalty;
                document.getElementById('groupPenalty').dispatchEvent(new Event('input'));
            }
            
            if (document.getElementById('suggestInnerPenalty').checked) {
                document.getElementById('innerPenalty').value = suggestions.inner_penalty;
                document.getElementById('innerPenalty').dispatchEvent(new Event('input'));
            }
            
            if (document.getElementById('suggestCheckHighways').checked) {
                document.getElementById('checkHighways').checked = suggestions.check_highways;
            }
        }
    }
    
    // 顯示成功提示
    alert('✓ 已應用選中的建議！');
    
    // 關閉面板
    document.getElementById('suggestionPanel').style.display = 'none';
});

// 關閉建議面板按鈕
document.getElementById('closeSuggestionBtn').addEventListener('click', function() {
    document.getElementById('suggestionPanel').style.display = 'none';
    clearVisualizationLayers();
});

// 初始化
document.addEventListener('DOMContentLoaded', function() {
    initMap();
    initMap2();
    loadConfigFromUrl();
    
    // 監聽優化模式切換
    document.getElementById('optimizationMode').addEventListener('change', function() {
        const clusteringSection = document.getElementById('clusteringSection');
        const globalMethodSection = document.getElementById('globalMethodSection');

        if (this.value === 'clustering') {
            clusteringSection.style.display = 'block';
            globalMethodSection.style.display = 'none';
        } else {
            clusteringSection.style.display = 'none';
            globalMethodSection.style.display = 'block';
        }
    });

    // 設置初始狀態（預設為分組模式）
    const clusteringSection = document.getElementById('clusteringSection');
    const globalMethodSection = document.getElementById('globalMethodSection');
    const defaultMode = document.getElementById('optimizationMode').value;

    if (defaultMode === 'clustering') {
        clusteringSection.style.display = 'block';
        globalMethodSection.style.display = 'none';
    } else {
        clusteringSection.style.display = 'none';
        globalMethodSection.style.display = 'block';
    }
    
    // 監聽終點模式切換
    document.querySelectorAll('input[name="endPointMode"]').forEach(radio => {
        radio.addEventListener('change', function() {
            const manualSection = document.getElementById('manualEndPointSection');
            
            console.log('終點模式切換:', this.value);
            
            if (this.value === 'manual') {
                manualSection.style.display = 'block';
            } else {
                manualSection.style.display = 'none';
                // 清除終點標記
                if (endMarker) {
                    map.removeLayer(endMarker);
                    endMarker = null;
                }
                // 清除輸入框
                document.getElementById('endLat').value = '';
                document.getElementById('endLon').value = '';
            }
        });
    });
    
    // 監聽終點輸入變化
    document.getElementById('endLat').addEventListener('input', function() {
        const lat = parseFloat(this.value);
        const lon = parseFloat(document.getElementById('endLon').value);
        if (!isNaN(lat) && !isNaN(lon)) {
            setEndPoint(lat, lon);
        }
    });
    
    document.getElementById('endLon').addEventListener('input', function() {
        const lat = parseFloat(document.getElementById('endLat').value);
        const lon = parseFloat(this.value);
        if (!isNaN(lat) && !isNaN(lon)) {
            setEndPoint(lat, lon);
        }
    });

    console.log('✅ 終點設置事件監聽器已註冊');

    // 綁定設定複製/導入按鈕
    document.getElementById('copySettingsBtn').addEventListener('click', function() {
        copySettingsToClipboard();
    });

    document.getElementById('importSettingsBtn').addEventListener('click', function() {
        importSettingsFromClipboard();
    });

    console.log('✅ 設定複製/導入按鈕已註冊');
});

// ========== 演算法步驟視覺化 ==========

let algorithmSteps = [];
let currentAlgorithmStep = 0;
let algorithmResultData = null;

// 初始化演算法視覺化器
function initAlgorithmViewer(steps, resultData) {
    algorithmSteps = steps;
    algorithmResultData = resultData;
    currentAlgorithmStep = steps.length - 1; // 默認顯示最後一步
    
    const progressBar = document.getElementById('algorithmProgressBar');
    const slider = document.getElementById('algoStepSlider');
    
    // 設置 slider 範圍
    slider.min = 0;
    slider.max = steps.length - 1;
    slider.value = currentAlgorithmStep;
    
    // 顯示進度條
    progressBar.style.display = 'flex';
    
    // 更新顯示
    updateAlgorithmStepDisplay();
    
    // 綁定事件
    bindAlgorithmEvents();
    
    console.log('✅ 演算法視覺化器已初始化，共', steps.length, '個步驟');
}

// 綁定演算法控制事件
function bindAlgorithmEvents() {
    const slider = document.getElementById('algoStepSlider');
    const prevBtn = document.getElementById('algoPrevBtn');
    const nextBtn = document.getElementById('algoNextBtn');
    const closeBtn = document.getElementById('algoCloseBtn');
    
    // Slider 拖動事件
    slider.addEventListener('input', function() {
        currentAlgorithmStep = parseInt(this.value);
        updateAlgorithmStepDisplay();
        visualizeAlgorithmStep(currentAlgorithmStep);
    });
    
    // Previous 按鈕
    prevBtn.addEventListener('click', function() {
        if (currentAlgorithmStep > 0) {
            currentAlgorithmStep--;
            slider.value = currentAlgorithmStep;
            updateAlgorithmStepDisplay();
            visualizeAlgorithmStep(currentAlgorithmStep);
        }
    });
    
    // Next 按鈕
    nextBtn.addEventListener('click', function() {
        if (currentAlgorithmStep < algorithmSteps.length - 1) {
            currentAlgorithmStep++;
            slider.value = currentAlgorithmStep;
            updateAlgorithmStepDisplay();
            visualizeAlgorithmStep(currentAlgorithmStep);
        }
    });
    
    // Close 按鈕
    closeBtn.addEventListener('click', function() {
        const progressBar = document.getElementById('algorithmProgressBar');
        progressBar.style.display = 'none';
        
        // 恢復最終結果顯示
        if (algorithmResultData) {
            const sequenceMode = currentConfig.sequenceMode || 'grouped';
            drawRoute(algorithmResultData, sequenceMode);
        }
    });
}

// 更新步驟顯示
function updateAlgorithmStepDisplay() {
    const step = algorithmSteps[currentAlgorithmStep];
    
    document.getElementById('algoStepNumber').textContent = 
        `(${currentAlgorithmStep + 1}/${algorithmSteps.length})`;
    
    const stepNameElement = document.getElementById('algoStepName');
    stepNameElement.textContent = step.name;
    
    const descElement = document.getElementById('algoStepDescription');
    const tooltip = document.getElementById('algoTooltip');
    
    descElement.textContent = step.description;
    
    // 移除舊的事件監聽器
    const newDescElement = descElement.cloneNode(true);
    descElement.parentNode.replaceChild(newDescElement, descElement);
    
    // 添加 hover tooltip 顯示影響參數
    if (step.affected_by && step.affected_by.length > 0) {
        newDescElement.style.cursor = 'help';
        
        // 添加視覺提示（小圖示）
        const infoIcon = document.createElement('span');
        infoIcon.textContent = ' ⓘ';
        infoIcon.style.color = '#3498db';
        infoIcon.style.fontSize = '14px';
        infoIcon.style.fontWeight = 'bold';
        infoIcon.style.cursor = 'help';
        
        newDescElement.appendChild(infoIcon);
        
        // 鼠標移入顯示
        newDescElement.addEventListener('mouseenter', function() {
            const params = step.affected_by.map(p => 
                `<span class="param-item">${p}</span>`
            ).join('');
            tooltip.innerHTML = `<div style="font-weight: 600; margin-bottom: 4px;">⚙️ 影響參數:</div>${params}`;
            tooltip.style.display = 'block';
        });
        
        // 鼠標移出隱藏
        newDescElement.addEventListener('mouseleave', function() {
            tooltip.style.display = 'none';
        });
    } else {
        newDescElement.style.cursor = 'default';
    }
    
    // 更新按鈕狀態
    document.getElementById('algoPrevBtn').disabled = (currentAlgorithmStep === 0);
    document.getElementById('algoNextBtn').disabled = (currentAlgorithmStep === algorithmSteps.length - 1);
}

// 視覺化當前步驟
function visualizeAlgorithmStep(stepIndex) {
    const step = algorithmSteps[stepIndex];
    
    console.log('視覺化步驟:', step.name, step.data);
    
    // 清除地圖上的舊標記
    clearOrderMarkers();
    
    switch(step.name) {
        case '初始化':
            visualizeInitialOrders(step.data);
            break;
        case 'DBSCAN 密度聚類':
            visualizeDBSCANClusters(step.data);
            break;
        case '噪聲點處理':
            visualizeNoiseReassignment(step.data, algorithmSteps[stepIndex - 1].data);
            break;
        case 'K-means 細分大群組':
            visualizeKMeansClusters(step.data);
            break;
        case '群組排序':
            visualizeGroupOrdering(step.data);
            break;
        case '完成訂單排序':
            visualizeFinalSequence(step.data);
            break;
        default:
            console.warn('未知的步驟類型:', step.name);
    }
}

// 視覺化初始訂單
function visualizeInitialOrders(data) {
    if (!data.orders) return;
    
    // 顯示所有訂單為灰色點
    data.orders.forEach((order, idx) => {
        const marker = L.circleMarker([order.lat, order.lon], {
            radius: 6,
            color: '#95a5a6',
            fillColor: '#95a5a6',
            fillOpacity: 0.6,
            weight: 2
        }).addTo(map);
        
        marker.bindPopup(`
            <div class="popup-title">訂單 ${idx + 1}</div>
            <div class="popup-tracking">${order.tracking_number}</div>
        `);
        
        orderMarkers.push(marker);
    });
}

// 視覺化 DBSCAN 聚類結果
function visualizeDBSCANClusters(data) {
    if (!data.result || !data.result.clusters) return;
    
    const clusters = data.result.clusters;
    const centers = data.result.centers || {};
    const colors = [
        '#e74c3c', '#3498db', '#2ecc71', '#f39c12', '#9b59b6', 
        '#1abc9c', '#e67e22', '#34495e', '#16a085', '#c0392b'
    ];
    
    let allOrders = [];
    
    Object.entries(clusters).forEach(([label, orders]) => {
        const color = label === '-1' ? '#95a5a6' : colors[parseInt(label) % colors.length];
        const isNoise = label === '-1';
        
        orders.forEach((order, idx) => {
            const marker = L.circleMarker([order.lat, order.lon], {
                radius: isNoise ? 4 : 8,
                color: color,
                fillColor: color,
                fillOpacity: isNoise ? 0.4 : 0.7,
                weight: isNoise ? 1 : 3
            }).addTo(map);
            
            marker.bindPopup(`
                <div class="popup-title">${isNoise ? '噪聲點' : `群組 ${label}`}</div>
                <div class="popup-tracking">${order.tracking_number}</div>
            `);
            
            orderMarkers.push(marker);
            allOrders.push(order);
        });
        
        // 顯示群組中心點（排除噪聲點）
        if (!isNoise && centers[label]) {
            const center = centers[label];
            const centerIcon = L.divIcon({
                className: 'center-marker',
                html: `<div style="
                    background: ${color};
                    width: 24px;
                    height: 24px;
                    border: 3px solid white;
                    border-radius: 50%;
                    box-shadow: 0 3px 8px rgba(0,0,0,0.5);
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    color: white;
                    font-size: 16px;
                    font-weight: bold;
                ">⊕</div>`,
                iconSize: [24, 24],
                iconAnchor: [12, 12]
            });
            
            const centerMarker = L.marker([center.lat, center.lon], {
                icon: centerIcon,
                zIndexOffset: 1000
            }).addTo(map);
            
            centerMarker.bindPopup(`
                <div class="popup-title">🎯 群組 ${label} 中心點</div>
                <div style="font-size: 12px; color: #555;">
                    座標: (${center.lat.toFixed(5)}, ${center.lon.toFixed(5)})<br>
                    訂單數: ${center.count}
                </div>
            `);
            
            orderMarkers.push(centerMarker);
        }
    });
}

// 視覺化噪聲點重新分配
function visualizeNoiseReassignment(data, previousData) {
    // 先顯示 DBSCAN 的結果
    visualizeDBSCANClusters(previousData);
    
    // 高亮顯示被重新分配的噪聲點
    if (data.reassignments) {
        data.reassignments.forEach(reassignment => {
            const marker = L.circleMarker([reassignment.lat, reassignment.lon], {
                radius: 10,
                color: '#ffc107',
                fillColor: '#ffc107',
                fillOpacity: 0.8,
                weight: 4
            }).addTo(map);
            
            marker.bindPopup(`
                <div class="popup-title">重新分配的噪聲點</div>
                <div class="popup-tracking">${reassignment.tracking_number}</div>
                <div style="font-size: 11px; margin-top: 4px;">
                    從噪聲 → 群組 ${reassignment.new_label}
                </div>
            `);
            
            orderMarkers.push(marker);
        });
    }
}

// 視覺化 K-means 細分結果
function visualizeKMeansClusters(data) {
    if (!data.final_clusters) return;
    
    const clusters = data.final_clusters;
    const operations = data.operations || [];
    const colors = [
        '#e74c3c', '#3498db', '#2ecc71', '#f39c12', '#9b59b6', 
        '#1abc9c', '#e67e22', '#34495e', '#16a085', '#c0392b',
        '#d35400', '#8e44ad', '#27ae60', '#2980b9', '#c0392b'
    ];
    
    const groupNames = ['A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'I', 'J',
                       'K', 'L', 'M', 'N', 'O', 'P', 'Q', 'R', 'S', 'T',
                       'U', 'V', 'W', 'X', 'Y', 'Z'];
    
    // 建立 clusterId 到中心點的映射
    const centerMap = {};
    operations.forEach(op => {
        if (op.action === 'keep' && op.center) {
            centerMap[op.final_cluster_id] = op.center;
        } else if (op.action === 'split' && op.sub_clusters) {
            op.sub_clusters.forEach(sub => {
                centerMap[sub.final_cluster_id] = sub.center;
            });
        }
    });
    
    let allOrders = [];
    
    Object.entries(clusters).forEach(([clusterId, orders]) => {
        const color = colors[parseInt(clusterId) % colors.length];
        const groupName = groupNames[parseInt(clusterId)] || clusterId;
        
        orders.forEach((order, idx) => {
            const marker = L.circleMarker([order.lat, order.lon], {
                radius: 8,
                color: color,
                fillColor: color,
                fillOpacity: 0.7,
                weight: 3
            }).addTo(map);
            
            marker.bindPopup(`
                <div class="popup-title">群組 ${groupName}</div>
                <div class="popup-tracking">${order.tracking_number}</div>
            `);
            
            orderMarkers.push(marker);
            allOrders.push(order);
        });
        
        // 顯示群組中心點
        const center = centerMap[parseInt(clusterId)];
        if (center) {
            const centerIcon = L.divIcon({
                className: 'center-marker',
                html: `<div style="
                    background: ${color};
                    width: 28px;
                    height: 28px;
                    border: 3px solid white;
                    border-radius: 50%;
                    box-shadow: 0 3px 8px rgba(0,0,0,0.5);
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    color: white;
                    font-size: 14px;
                    font-weight: bold;
                ">${groupName}</div>`,
                iconSize: [28, 28],
                iconAnchor: [14, 14]
            });
            
            const centerMarker = L.marker([center.lat, center.lon], {
                icon: centerIcon,
                zIndexOffset: 1000
            }).addTo(map);
            
            centerMarker.bindPopup(`
                <div class="popup-title">🎯 群組 ${groupName} 中心點</div>
                <div style="font-size: 12px; color: #555;">
                    座標: (${center.lat.toFixed(5)}, ${center.lon.toFixed(5)})<br>
                    訂單數: ${orders.length}
                </div>
            `);
            
            orderMarkers.push(centerMarker);
        }
    });
}

// 視覺化群組排序
function visualizeGroupOrdering(data) {
    if (!data.group_order || !data.cluster_centers) return;
    
    const groupOrder = data.group_order;
    const centers = data.cluster_centers;
    const colors = [
        '#e74c3c', '#3498db', '#2ecc71', '#f39c12', '#9b59b6', 
        '#1abc9c', '#e67e22', '#34495e', '#16a085', '#c0392b',
        '#d35400', '#8e44ad', '#27ae60', '#2980b9', '#c0392b'
    ];
    
    // 繪製群組中心點並標示順序
    groupOrder.forEach((groupInfo, idx) => {
        const center = groupInfo.center;
        if (!center) return;
        
        const color = colors[idx % colors.length];
        
        // 群組中心點標記
        const centerIcon = L.divIcon({
            className: 'group-ordering-marker',
            html: `<div style="
                background: ${color};
                width: 40px;
                height: 40px;
                border: 4px solid white;
                border-radius: 50%;
                box-shadow: 0 4px 12px rgba(0,0,0,0.6);
                display: flex;
                align-items: center;
                justify-content: center;
                color: white;
                font-size: 18px;
                font-weight: bold;
            ">${groupInfo.group}</div>`,
            iconSize: [40, 40],
            iconAnchor: [20, 20]
        });
        
        const marker = L.marker([center.lat, center.lon], {
            icon: centerIcon,
            zIndexOffset: 1000
        }).addTo(map);
        
        marker.bindPopup(`
            <div class="popup-title">群組 ${groupInfo.group} (順序 #${idx + 1})</div>
            <div style="font-size: 12px; color: #555;">
                座標: (${center.lat.toFixed(5)}, ${center.lon.toFixed(5)})<br>
                訂單數: ${groupInfo.size}<br>
                群組ID: ${groupInfo.cluster_id}
            </div>
        `);
        
        orderMarkers.push(marker);
        
        // 添加順序標籤（在標記旁邊）
        const labelIcon = L.divIcon({
            className: 'sequence-label',
            html: `<div style="
                background: rgba(0,0,0,0.7);
                color: white;
                padding: 4px 8px;
                border-radius: 12px;
                font-size: 12px;
                font-weight: bold;
                white-space: nowrap;
                box-shadow: 0 2px 6px rgba(0,0,0,0.4);
            ">#${idx + 1}</div>`,
            iconSize: [30, 20],
            iconAnchor: [-10, 30]
        });
        
        const labelMarker = L.marker([center.lat, center.lon], {
            icon: labelIcon,
            zIndexOffset: 999
        }).addTo(map);
        
        orderMarkers.push(labelMarker);
    });
    
    // 繪製連接線顯示順序
    if (groupOrder.length > 1) {
        const lineCoords = groupOrder
            .filter(g => g.center)
            .map(g => [g.center.lat, g.center.lon]);
        
        const polyline = L.polyline(lineCoords, {
            color: '#2c3e50',
            weight: 3,
            opacity: 0.6,
            dashArray: '10, 10',
            smoothFactor: 1
        }).addTo(map);
        
        orderMarkers.push(polyline);
    }
    
    // 調整地圖視角以顯示所有群組
    if (groupOrder.length > 0) {
        const bounds = L.latLngBounds(
            groupOrder
                .filter(g => g.center)
                .map(g => [g.center.lat, g.center.lon])
        );
        map.fitBounds(bounds, { padding: [50, 50] });
    }
}

// 視覺化最終排序
function visualizeFinalSequence(data) {
    if (!algorithmResultData) return;
    
    // 使用最終結果繪製路徑
    const sequenceMode = currentConfig.sequenceMode || 'grouped';
    drawRoute(algorithmResultData, sequenceMode);
}

console.log('✅ 演算法視覺化模組已載入');

