// модульные тесты не ходят в сеть: fetch по умолчанию отвергает запросы
// тест-файлы могут переопределить fetch своим vi.stubGlobal
import { vi } from "vitest";

vi.stubGlobal(
  "fetch",
  vi.fn(() => Promise.reject(new Error("тесты без сети"))),
);
