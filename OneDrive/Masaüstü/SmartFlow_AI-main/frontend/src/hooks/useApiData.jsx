import { useState, useEffect, useCallback, useRef, createContext, useContext } from 'react';
import {
  getDashboardSummaryResult, getTasksResult, getOrdersResult, getProductsResult, getShipmentsResult,
} from '../api/client.js';

const DataContext = createContext(null);

const RESOURCE_KEYS = ['summary', 'tasks', 'orders', 'products', 'shipments'];

const emptyStatuses = () => Object.fromEntries(RESOURCE_KEYS.map(key => [key, {
  ok: false,
  loading: true,
  error: null,
  source: 'loading',
  receivedAt: null,
}]));

const EMPTY = {
  summary: null,
  tasks: [],
  orders: [],
  products: [],
  shipments: [],
  loading: true,
  refreshing: false,
  resources: emptyStatuses(),
  lastUpdated: null,
  hasError: false,
  isPartial: false,
};

function statusFromResult(result) {
  return {
    ok: result.ok,
    loading: false,
    error: result.error,
    status: result.status,
    source: result.source,
    receivedAt: result.receivedAt,
  };
}

export function DataProvider({ children }) {
  const [data, setData] = useState(EMPTY);
  const timerRef = useRef(null);
  const hasLoadedRef = useRef(false);

  const load = useCallback(async () => {
    const hadData = hasLoadedRef.current;
    setData(prev => ({ ...prev, loading: !hadData, refreshing: hadData }));

    const [summary, tasks, orders, products, shipments] = await Promise.all([
      getDashboardSummaryResult(),
      getTasksResult(),
      getOrdersResult(),
      getProductsResult(),
      getShipmentsResult(),
    ]);

    const results = { summary, tasks, orders, products, shipments };
    const resources = Object.fromEntries(
      RESOURCE_KEYS.map(key => [key, statusFromResult(results[key])])
    );
    const hasError = RESOURCE_KEYS.some(key => !results[key].ok);

    hasLoadedRef.current = true;
    setData({
      summary: summary.ok ? summary.data : null,
      tasks: tasks.ok && Array.isArray(tasks.data) ? tasks.data : [],
      orders: orders.ok && Array.isArray(orders.data) ? orders.data : [],
      products: products.ok && Array.isArray(products.data) ? products.data : [],
      shipments: shipments.ok && Array.isArray(shipments.data) ? shipments.data : [],
      loading: false,
      refreshing: false,
      resources,
      lastUpdated: new Date().toISOString(),
      hasError,
      isPartial: hasError && RESOURCE_KEYS.some(key => results[key].ok),
    });
  }, []);

  useEffect(() => {
    load();
    timerRef.current = setInterval(load, 120000);
    return () => clearInterval(timerRef.current);
  }, [load]);

  return (
    <DataContext.Provider value={{ ...data, refresh: load }}>
      {children}
    </DataContext.Provider>
  );
}

export function useApiData() {
  return useContext(DataContext);
}
