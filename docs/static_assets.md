# DEP-05 静态资源本地化合同

## 1. 目的

生产页面不得在运行时从公共CDN加载CSS或JavaScript。本阶段将Bootstrap 5.3.3冻结在
`static/vendor/bootstrap/5.3.3`，使页面样式和导航交互不依赖用户浏览器访问第三方服务。

## 2. 资源来源和版本

冻结包：`bootstrap@5.3.3`。文件从原模板使用的jsDelivr npm发布路径下载：

```text
https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/css/bootstrap.min.css
https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/css/bootstrap.min.css.map
https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/js/bootstrap.bundle.min.js
https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/js/bootstrap.bundle.min.js.map
https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/LICENSE
```

这些URL只用于记录来源，不会出现在页面运行时请求中。

## 3. 完整性摘要

| 文件 | SHA-256 |
| --- | --- |
| `css/bootstrap.min.css` | `3c8f27e6009ccfd710a905e6dcf12d0ee3c6f2ac7da05b0572d3e0d12e736fc8` |
| `css/bootstrap.min.css.map` | `f12338536350a422c64d02d6e43ff1dea493c3156ad823fe19761cdd5d56c05b` |
| `js/bootstrap.bundle.min.js` | `0833b2e9c3a26c258476c46266e6877fc75218625162e0460be9a3a098a61c6c` |
| `js/bootstrap.bundle.min.js.map` | `5e3e0763164143baaa1ca0706b6100ba0452f911d6ce9713b48e3dbe07b35125` |
| `LICENSE` | `8c14611ae41ac6fd543c13349f22188eb12c69b3e59105c5eca3925a8e4eca3e` |

合同测试会验证全部摘要，防止静态文件被静默替换。版本升级必须同时更新目录、
模板引用、许可证、摘要和回归测试，不得直接覆盖当前版本目录。

## 4. 验收

1. 所有HTML模板不包含外部CSS或JavaScript运行时引用。
2. 首页渲染为`/static/vendor/bootstrap/5.3.3/...`路径。
3. `collectstatic`复制CSS、JavaScript、source map和许可证。
4. 生产镜像包含冻结资源，Nginx可通过`/static/`提供它们。
5. 禁用外网后首页、学生登录、管理员登录和折叠导航仍可正常使用。
