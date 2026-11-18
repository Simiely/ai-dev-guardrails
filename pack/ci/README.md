# CI 门禁

只需要先上三条，够挡住大部分漂移：

| 检查 | 判定 | 作用 |
|---|---|---|
| 依赖方向 | 反向 import 即失败 | 防跨层 |
| 循环依赖 | 检测到即失败 | 防纠缠 |
| 未登记模块 | `registry.yaml` 里没有的模块目录即失败 | 防私建 |

## 各技术栈的最小配置

### TypeScript / JavaScript — dependency-cruiser

```js
// .dependency-cruiser.js
module.exports = {
  forbidden: [
    { name: 'no-circular', severity: 'error', from: {}, to: { circular: true } },
    { name: 'no-reverse', severity: 'error',
      from: { path: '^modules/domain' },
      to: { path: '^modules/(application|adapter)' } },
    { name: 'no-internal', severity: 'error',
      from: { path: '^modules/([^/]+)/' },
      to: { path: '^modules/(?!$1)/', pathNot: 'CONTRACT' } },
  ],
};
```

### Python — import-linter

```toml
# pyproject.toml
[tool.importlinter]
root_packages = ["app"]

[[tool.importlinter.contracts]]
name = "依赖方向"
type = "layers"
layers = ["app.adapter", "app.application", "app.domain"]
```

### Java / Kotlin — ArchUnit

```java
@AnalyzeClasses(packages = "com.example")
class ArchitectureTest {
  @ArchTest
  static final ArchRule layers = layeredArchitecture()
      .layer("Adapter").definedBy("..adapter..")
      .layer("Application").definedBy("..application..")
      .layer("Domain").definedBy("..domain..")
      .whereLayer("Domain").mayNotAccessAnyLayer()
      .whereLayer("Application").mayOnlyAccessLayers("Domain")
      .whereLayer("Adapter").mayOnlyAccessLayers("Application", "Domain");
}
```

## 未登记模块检查

不依赖语言，直接跑：

```powershell
.\scripts\check-unregistered-modules.ps1
```

## 顺序

1. 先上这三条，跑一周
2. 稳定后加：受影响测试
3. 再加：spec 漂移检查

不要一次全上，否则会变成「天天在修流水线」。
