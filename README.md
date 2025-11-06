# jizhang

本仓库包含 iOS 记账应用的开发规划与设计文档，并提供一个可直接在浏览器中运行的轻量级记账 Demo。

## 浏览器端 Demo

1. 下载或克隆仓库后，进入 `web/` 目录。
2. 直接双击 `index.html`，即可在浏览器中离线运行；如需通过本地服务器访问，可运行 `python -m http.server` 后打开 `http://localhost:8000/web/`。
3. Demo 支持添加/删除账目、筛选查看、浏览器本地持久化，并可导出 JSON 备份或导入已有数据。

> 提示：所有数据保存在浏览器的 `localStorage` 中，清理浏览器缓存或更换设备前请先导出备份。

## 设计与规划文档

详细方案见 [docs/ios-accounting-app-plan.md](docs/ios-accounting-app-plan.md)，涵盖功能规划、架构设计、迭代路线及下载发布指引。
