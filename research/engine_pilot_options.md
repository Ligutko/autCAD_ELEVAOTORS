# Пілот «комп'ютер у комп'ютері»: веб-пульт на моніторі в 3D-кабінеті, варіанти рушія

Дата дослідження: 2026-09-29. Агент: general-purpose (лише читання інтернету, код проєкту не змінювався).
Мета: вибрати найменш ризикований шлях для пілоту «кімната + монітор із живою сторінкою пульта + одна анімована норія».
Рішення про рушій не приймається цим звітом; тут факти, ризики й рекомендація.

## Позначки надійності

- **[П]** підтверджено джерелом: сторінку, сирий файл чи відповідь GitHub API я прочитав 2026-09-29 (у списку джерел вказано URL і дату самого матеріалу).
- **[Ч]** чути, але не підтверджено: вторинне джерело (блог, підсумок пошуковика, чужа таблиця порівняння) або мій власний висновок. Такі місця позначені прямо.
- **не знайдено** означає, що я шукав і не знайшов, а не що цього немає.

Застереження щодо інструментів. Частина сторінок Epic (docs, license, FAQ) віддає 403 або порожню оболонку без тексту (сторінки рендеряться скриптом). Де я не міг прочитати першоджерело, я це пишу. Підсумки WebFetch кілька разів перекручували роки (наприклад, «2024» замість 2026), тому дати релізів я перевіряв окремо через GitHub API, а не з переказу.

## 0. Що саме має вміти вбудований браузер (з коду проєкту, прочитано)

Джерело: `world/sim/server.py`, `world/panel/*`. [П]

- Сервер на stdlib слухає **лише 127.0.0.1:8765**. Віддає `GET /state` (JSON), `GET /graph`, `GET /mnemo.svg`, `POST /cmd`, `POST /scenario`, статику пульта.
- Відповіді **без CORS-заголовків і без X-Frame-Options**. Пульт звертається до сервера **відносними URL** (`fetch("/state")`), тобто працює в iframe тієї ж адреси без змін.
- Пульт опитує `/state` кожні **250 мс** (`setTimeout(poll, 250)`), тобто 4 Гц. Гладкий 60 к/с браузера йому не потрібен.
- Зовнішніх ресурсів немає: `index.html` + `panel.css` + `panel.js` ≈ 24 КБ; шрифт `"Segoe UI", system-ui, sans-serif` (системний, веб-шрифтів немає).
- Елементи, що вимагають від вбудованого браузера більше, ніж просто клік: `<select id="scenario">` (випадний список), `<input id="feed">` (введення числа з клавіатури), підказки `title=` при наведенні (необов'язкові).
- Схема `/state` (`world/sim/STATE_SCHEMA.json`): 17 верхніх ключів; `motors`, `gates`, `edges`, `stores`, `totals`, `trucks` є **словниками за id** (`dryer` і `sensors` теж вкладені об'єкти), а `alarms`, `events`, `routes` масивами. Це важливо для парсингу в рушії (див. Unity нижче).
- Мнемосхема будується сервером із `layout.json`: **42 вузли, 59 ребер**. Це межа обсягу запасного варіанту «нативний переклад».

Висновок для вибору: перевірка пілоту мусить включати не лише «клік по кнопці», а й (а) відкриття `<select>`, (б) введення цифр у `#feed`, (в) читабельність тексту 13 px на 3D-моніторі. Саме такі місця в браузерах «у текстурі» ламаються найчастіше.

## 1. Зведена таблиця

| Рушій / шлях | Веб-екран на 3D-поверхні | Ціна | Головні ризики | Вердикт для пілоту |
|---|---|---|---|---|
| **Unity 6.3 LTS + Vuplex 3D WebView for Windows** | Так, штатно: `WebViewPrefab` рендерить у Texture2D, клік/скрол/hover/drag, клавіатура, `<select>` [П] | Unity Personal безкоштовний до $200k доходу/фінансування, Pro $2 310/рік [П]. Vuplex: $159.99 на store.vuplex.com, $179.99 в Unity Asset Store, ліцензія на розробника [П, розбіжність цін]. Триал 14 днів [П] | Закритий код плагіна; +250–360 МБ до збірки; на DX12 без апаратного прискорення [П]; залежність від одного вендора; **мною не випробувано** | **Найменш ризикований серед рушіїв** для самого монітора. Рекомендовано для пілоту |
| **Unreal 5.8, вбудований Web Browser (CEF)** | Так: Widget Component + Web Browser widget + Widget Interaction Component [П, старі джерела] | Рушій безкоштовний; роялті 5% понад $1 млн для ігор; для інтерактивного тренажера-симулятора категорія ліцензії **не з'ясована** (сторінка Epic дала 403) [Ч] | На Windows до 5.6 включно Chromium 90, CEF 128 лише за ручним прапором і з крашами GPU-процесу [П]; для 5.8 не знайдено; віджет у палітрі «Experimental» [П, старі сторінки]; ліміт 15 Гц циклу браузера [П]; клавіатура через WIC [П] | Найгірше документований шлях для монітора. Брати лише як паралельну перевірку, якщо головний пріоритет Lumen/Nanite |
| **Unreal 5.8 + BLUI-Unreal (сторонній CEF 128)** | Так: браузер у текстуру/матеріал, «paint it on anything» (README) [П] | Безкоштовно, MIT [П] | Один основний автор; ввід у 3D-вікні не перевірено; CEF 128 (Chromium 128) вже не свіжий [П] | Запасний варіант №1 у Unreal. Живий: реліз v5.1.0 «для UE 5.8» від 2026-09-25 [П] |
| **Godot 4.7 + godot-cef (Rust, CEF 152)** | Так, заявлено як основне використання («web content as a texture in 3D scenes») [П]; покрокового опису 3D-вводу не знайдено | Безкоштовно, MIT [П] | Проєкт молодий (створено 2025-12-31); відкриті помилки синхронізації GPU, джитер, затримка вводу в 1 кадр, підвисання скролу на Windows [П]; DX12 на Windows потребує Godot ≥ 4.6 [П] | Запасний/експериментальний. Не для першого пілоту |
| **Godot + gdcef (C++, старший)** | Так, є 3D-демо з просторовим звуком [П] | Безкоштовно, MIT; CEF містить LGPL-залежності [П] | Лише програмний рендер, немає HiDPI (за таблицею конкурента) [Ч]; у трекері «Maintainers wanted» [П] | Не рекомендовано |
| **Веб: three.js + CSS3DRenderer + iframe** | Так, офіційний приклад `css3d_mixed` робить саме «WebGL-кімната + справжній iframe у 3D» [П, код прикладу] | Безкоштовно, MIT | Немає оклюзії (3D-об'єкти не закривають iframe); крихкі CSS-трансформи в різних браузерах; масштаб сцени (55 тис. дерев); мобільний iframe не перевірено | Найдешевша перевірка ідеї монітора; єдиний варіант «відкривається на телефоні без встановлення». Як контроль або як окремий кінцевий продукт |
| **Запасний: нативний пульт у UI рушія** | Не потрібен браузер: UI читає той самий `/state` і шле `POST /cmd` | Час розробки; плагінів не треба (Unity: UnityWebRequest + Newtonsoft; Unreal: HTTP+JSON) [П] | Дублювання логіки пульта: кожна зміна `panel.js` робиться двічі; SVG-мнемосхема в Unreal без стороннього плагіна не малюється [П] | Страховка на випадок, якщо тест монітора провалиться |

## 2. Unreal Engine 5.x (пункт 1)

### Статус вбудованого Web Browser

- Плагін `WebBrowserWidget` і клас `UWebBrowser` (`Engine/Plugins/Runtime/WebBrowserWidget`) присутні в документації API **UE 5.8**; позначок «experimental/deprecated» на цій сторінці немає. [П]
- Поточна версія Unreal: **5.8** (у документації Epic всі сторінки з написом 5.8; стаття CG Channel «Unreal Engine 5.8 is here» від 2026-06-17). [П] Сторінка релізних нотаток 5.8 не згадує WebBrowser/CEF (пошук по тексту дав 0 збігів). [П]
- Категорія віджета в палітрі UMG: «Experimental» (за вікі спільноти ~2021 і за підсумком пошуку про `GetPaletteCategory` у `WebBrowser.cpp`; сторінку API 4.26 я не відкривав). [Ч, джерела старі] Офіційного окремого заяву «плагін має статус X» для 5.8 я **не знайшов**.
- **Версія CEF, документація суперечить практиці.** Співробітник Epic 2025-06-23 написав: «ми оновили CEF до v128 в UE 5.6». Але (за читанням `CEF3.Build.cs` користувачем, підтвердження співробітника Epic «Yes, that is correct») для Win64 прапор `bUseExperimentalVersion = false`, і на Windows у збірці 5.5 і 5.6 лишається **CEF 90.6.7 / Chromium 90**; реліз v128 «зробили, а потім відкотили до завершення». [П, форум 2025-06-20…25] Інженер Epic (rpokrzywka_eg) дав коміти для ручного перенесення.
- Спроба ввімкнути CEF 128 на **5.6.1**: краш GPU-процесу (`exit_code=777006`), відтворено на чистому проєкті; відповіді від Epic немає. [П, форум 2025-09-17/18, дві гілки]
- Для **5.7** один користувач 2025-09-24 написав «5.7 preview підтримує CEF 128 (finally!)» [Ч, не підтверджено Epic]. Побічна ознака: сторонній плагін BLUI випустив «v5.0.0 for UE 5.7» з CEF 128.4.12 (2025-12-05). Нотатки патчів 5.7.1–5.7.4 містять збої `FWebBrowserSingleton` та зауваження про сміттєвий `webcache` у папці проєкту. [П]
- Для 5.8, чи вмикається CEF 128 на Windows за замовчуванням: **не знайдено**.

### Як показати сторінку на моніторі

1. Плагін Web Browser увімкнути в Plugins, перезапустити редактор. [П, вікі]
2. Створити User Widget (WBP), покласти в нього віджет **Web Browser** (Initial URL, наприклад `http://127.0.0.1:8765/`). [П, вікі]
3. Створити Actor: `StaticMesh` монітора плюс **Widget Component** (Widget Class = WBP, Space = World, Draw Size = розмір текстури, наприклад 1920×1080, Redraw Time керує частотою оновлення). [П, документація Widget Components 5.8: Space, Draw Size, Redraw Time, Window Focusable]
4. У пешки гравця додати **Widget Interaction Component**: він кидає промінь і «натискає» задану клавішу; для кліку викликати `Press Pointer Key` / `Release Pointer Key` (ліва кнопка миші). Без цих двох викликів клік не працює. [П, документація 4.27 «Creating 3D Widget Interaction»; для 5.x сторінка перенесена]
5. Що всередині WBP вважається екраном, що поза ним ні: віджет лягає на площину, а не на довільний UV меша. Точне вирівнювання з екраном моніторної моделі робиться розміром і позицією компонента. [Ч, мій висновок з документації]

### Відомі проблеми (з датами)

- **Продуктивність.** У `WebBrowserSingleton.cpp` цикл повідомлень CEF за замовчуванням **15 Гц** (`MaxForcedMessageLoopHertz = 15`, стеля 60). Користувач 2020-07 бачив 15 к/с браузера при 30 к/с гри; обхід: `BrowserFrameRate(...)` у C++ або `GConfig->SetInt("Browser","MaxForcedMessageLoopHertz",60,GEngineIni)` (пост 2026-03-20). Навіть так анімація в сторінці сильно просаджує кадри. [П, форум 2020–2026] Для пульта з опитуванням 4 Гц це терпимо. [Ч, мій висновок]
- **HiDPI / чіткість.** Віджет у світі рендериться в render target розміру Draw Size, чіткість тексту залежить від нього. Стара скарга (2016–2017) «розмите, темне» пояснена тим, що плагін віддає sRGB, а 3D-віджет чекає лінійний: лікується власним матеріалом. [П, старий форум]. Розмір вмісту на Android відрізняється від редактора (2024-05, без відповіді Epic) [П].
- **Клавіатура й фокус.** Widget Interaction Component навмисно не віддає справжню клавіатуру віджетові (пояснення розробника Epic, 2016): потрібні `Send Key Char` або своя копія WIC. Свіжий пост **2026-01-02** (UE 5.5): у TextBox на 3D-моніторі через WIC символи не вводяться, працює лише з `Add to Viewport`; відповідей немає. [П] Для нашого `#feed` це реальний ризик.
- **WIC + Web Browser.** 2018-02 (UE 4.18): WIC клікає або по браузеру, або по іншому віджету, не по обох; невирішено в 4.22–4.23 (2019-10). [П, стара помилка; чи лишилась у 5.8 невідомо]
- **Пакування для Windows.** Помилка `Can't deploy D:\Resources\locales\af.pak…` при стейджингу вирішена комітом у гілці 5.6 (2025-06-25). Локальні HTML треба віддавати як «неасет-файли» (стаття 2021, UE 4.26). Читач 2025-11 повідомив: при перенесенні плагіна 5.7 у 5.4 пакування падало, поки не додали `WinPixGpuCapturer.dll`. [П] У нашому випадку сторінку віддає локальний сервер, тож файли в пакет не потрібні, але сервер має бути запущений окремо. [Ч]
- Linux 5.6.0 не завантажує локальні файли в пакованій збірці (заголовок гілки форуму). [П, нам не потрібно]

### Сторонні варіанти для Unreal

- **BLUI-Unreal** (getnamo): MIT, 424 зірки, останній push 2026-09-25, реліз **v5.1.0 «for UE5.8»** (2026-09-25), CEF 128.4.12 у власній `blucef.dll`, браузер дає текстуру/матеріал для будь-якого меша. [П, GitHub API і README]
- **WebUserInterfaceUnreal** (ArtemIyX): MIT, UE 5.7.4+, окремий `Host.exe`, 2 зірки, створено 2026-04-08; про 3D-світ у README нічого. [П] Занадто молодий.
- **UCefView** (12 зірок), **starTechnology1994/uewebbrowser** (31 зірка, рекламний пост на форумі 2026-08-27): не оцінював. [П лише статистика]

### Ціна Unreal

Стаття CG Channel (2026-06-17, вторинне джерело): для ігор Epic бере 5% валового доходу після перших $1 млн; для неінтерактивного контенту безкоштовно до $1 млн доходу студії, далі $1 850 за місце на рік. [П як переказ] Умови для «інтерактивного тренажера, що не є грою» я не з'ясував: `unrealengine.com/license` і FAQ віддали 403. [не знайдено]

## 3. Unity (пункт 2)

### Актуальна версія

Unity 6.3 LTS: останній LTS, підтримка до грудня 2027; 6.0 LTS до жовтня 2026. [П, unity.com/releases/unity-6/support] Блог makaka.org (оновлено 2026-09-18) називає 6.6 (вийшла 2026-09-01) і очікує 6.7 LTS та Unity 7 у 2027. [Ч, вторинне джерело]
Ціни Unity: Personal безкоштовний до $200 000 доходу й фінансування; Pro $2 310/рік або $210/міс. за місце (з 2026-01-12); Runtime Fee скасовано 2024-09-12. [П, unity.com/products/pricing-updates]

### Вбудований веб-в'ю на 3D-поверхні

Вбудованого компонента, що малює веб-сторінку на 3D-поверхні у Windows standalone, **не знайдено** (жодна з прочитаних сторінок Unity такого не описує). Усе робиться плагінами.

### Vuplex 3D WebView for Windows and macOS

- Версія **4.15.2**, оновлено **2026-06-12**, мінімум Unity 2022.3.62 у картці Asset Store; на сайті вендора «Unity 2019.4 або новіша». [П, дві сторінки; розбіжність мінімальних версій]
- Chromium **v137** на Windows; Windows 10+ x64; Direct3D11 і Direct3D12; Mono та IL2CPP. **До 144 к/с на D3D11 з апаратним прискоренням; D3D12 «рендерить повільніше, без прискорення»**, тож для пілоту слід ставити DX11. [П, store.vuplex.com]
- Chromium додає **≈360 МБ** до збірки (можна скоротити до ≈250). [П]
- **3D-поверхня та ввід:** `WebViewPrefab` рендерить у Texture2D і сам обробляє клік, перетягування, скрол; клавіатура ввімкнена за замовчуванням (`KeyboardEnabled = true`); детектор вказівника можна замінити (`SetPointerInputDetector`) для власного променя з камери; властивість `Material` дозволяє повісити на довільну поверхню; `Resolution` у пікселях на одиницю Unity (типово 1300). [П, developer.vuplex.com/webview/WebViewPrefab] Готового кроку «повісити на конкретний меш монітора» у документації не бачив. [Ч]
- **`<select>` та підказки.** Сторінка підтримки (оновлена 2024-06-06) описує обмеження для 3D-режиму: нативні випадні списки, `input type=date/color…`, hover-підказки `title` не малюються, але прямо сказано: «обмеження **не стосується** 3D WebView for Windows and macOS». [П, сирий текст сторінки]. Для нашого `<select id="scenario">` і `title=` це добра новина, але перевірити у триалі треба. [Ч]
- JavaScript-міст двосторонній (C# ↔ JS), `SendDevToolsMessage`, віддалене налагодження (`EnableRemoteDebugging`). [П]
- **Ліцензія:** «Vuplex Commercial Library License», без роялті, ліцензія на розробника; вихідного коду нативних плагінів немає; текст ліцензії Chromium треба показати у титрах. [П, зведення сторінок; сама сторінка ліцензії завантажується скриптом, дослівного тексту я не читав]
- **Ціна:** $159.99 (store.vuplex.com, сирий HTML), $179.99 (Unity Asset Store), огляд каталогу показує діапазон $129.99–$229.99 для різних платформ (кожна платформа продається окремо). Розбіжність цін між двома магазинами документація не пояснює. [П]
- **Триал:** 14 днів від створення, після цього перестає працювати, «не призначений для розробки продукту»; окремий триал на кожен пакет. [П]
- Відгуки: 243 в Asset Store, оцінка 5 зірок. [П]

### Інші варіанти для Unity

- **gree/unity-webview** (Zlib, 2 668 зірок, живий): на Windows WebView2 у режимі offscreen у вигляді текстури, але в README сказано, що плагін **не підтримує віджети в 3D**; в одній сторінці тут внутрішня суперечність (offscreen-текстура і «не в 3D»), не перевіряв. Потребує WebView2 Runtime і ручної збірки DLL. [П]
- **Voltstro UnityWebBrowser** (MIT, CEF, Unity 2021.3+, 458 зірок, останній push 2026-06-18): про світовий простір у README нічого; сумісність з Unity 6 не заявлена. [П]
- **UniWebView**: за китайським оглядом лише накладка на екран, не світовий простір. [Ч]

### Читання `/state` у Unity (для нативного варіанта і для анімації норії)

`UnityWebRequest` (GET у корутині), але **`JsonUtility` не вміє Dictionary**, а в `/state` більшість блоків це словники за id. Треба офіційний пакет `com.unity.nuget.newtonsoft-json` (13.0.1). [П, Unity Discussions і документація пакета]

## 4. Godot 4.x (пункт 3)

- Поточна стабільна версія **4.7.2** (2026-08-18); 4.7 вийшла 2026-06-18. [П, godotengine.org/download/archive]
- Вбудованого браузера в Godot немає (розширення не входять у ядро). [Ч, не бачив прямого твердження в документації]
- **godot-cef** (dsh0416): Rust GDExtension на CEF; вузол `CefTexture` (наслідує `TextureRect`); MIT; Godot **4.5+**; Windows: DirectX 12 (потрібен Godot ≥ 4.6 beta 2, у 4.5.1 помилка `get_driver_resource`), Vulkan через хук (лише x86_64), програмний фолбек; без пропрієтарних кодеків (H.264/AAC/MP3); ≈100 МБ+; IPC на CBOR; IME. Створено 2025-12-31, 227 зірок, останній реліз **v1.16.2 від 2026-09-26**, CEF 152.3.0 за трекером. [П, README, GitHub API]
  - Відкриті проблеми в трекері: **#193** «Input and Texture synchronization», затримка ≈1 кадр між вводом і графікою, «дивний джитер і миготіння»; **#227** трекер синхронізації GPU для прискореного OSR; **#181** «judder при скролі», Godot 4.6, Windows; **#207** підвисання при швидкому подвійному перетягуванні; #162 «enable_accelerated_osr renders nothing». [П, GitHub API]
  - Про 3D: у README лише «web content as a texture in 3D scenes» і скріншот; сторінка API про 3D/SubViewport/введення в 3D **нічого не каже**. [П] Практичний шлях (мій висновок [Ч]): `CefTexture` у `SubViewport`, текстура вьюпорту на меші, промінь від камери переводить у координати вьюпорту і передає `viewport.push_input(...)`, як у офіційній демо «GUI in 3D» (яка працює з Godot 4, Compatibility renderer) [П для демо].
- **gdcef** (Lecrapouille): C++ GDExtension на CEF; MIT (CEF має LGPL-залежності); Godot 4.2+; Linux і Windows; демо «Browser in a 3D scene with spatial audio»; версія 0.20.0 (2026-08-20), 441 зірка; є відкрита задача «(Co)-Maintainers wanted». [П] У таблиці порівняння автора godot-cef про gdcef написано «лише програмний рендер, немає HiDPI, немає експорту проєкту»: це слова конкурента. [Ч]
- **godot_wry** (MIT, 525 зірок): системний веб-в'ю поверх вікна; за таблицею godot-cef «не в 3D-сцені, завжди зверху». [Ч]

## 5. Веб-варіант: three.js (пункт 4)

### Що можна зробити (все підтверджено кодом офіційних прикладів)

- Приклад `css3d_youtube` (three.js): справжній `<iframe>` у `CSS3DObject`, чотири екрани у просторі; під час перетягування камери показується «блокувальник» (`blocker`), щоб iframe не перехоплював події. [П, сирий код прикладу]
- Приклад **`css3d_mixed`**: два рендерери один над одним: `CSS3DRenderer` (знизу, з iframe `./#webgl_animation_keyframes`, тобто **та сама адреса**) і `WebGLRenderer` з `alpha: true` та `pointerEvents: 'none'` зверху; у WebGL-сцені площина з `NoBlending, opacity 0, premultipliedAlpha` «пробиває дірку», через яку видно iframe; під час обертання камери у iframe ставиться `pointerEvents='none'`. Це рівно схема «кімната з екраном, на якому справжня сторінка». [П, сирий код прикладу]
- **Клік.** У схемі CSS3D iframe це справжній DOM-елемент, клік іде прямо в нього, **raycast не потрібен**. Розплата: 3D-об'єкти перед екраном не закривають його від кліків (оклюзії немає). [П: документація three.js «no depth/occlusion»; прикметою обмеження є коментар на форумі «css3d can't occlude»]
- Якщо потрібна справжня оклюзія: текстура з DOM. Бібліотека `three-html-render` (MIT, 189 зірок): HTML → SVG `foreignObject` → канвас → текстура; `RaycastInteractionManager` переносить клік з місця на текстурі назад у DOM; про iframe в README нічого. [П, README] Прямо в текстуру iframe вбудувати неможливо («Not really», форум three.js). [П]
- Ліміти CSS3DRenderer за документацією three.js: немає матеріалів і геометрій, працює лише зі звичайним DOM, лише зум браузера 100%. [П]

### Обмеження й помилки

- Помилка «сліпа зона» інтерактивності (#26583, three.js r145, 2023-08): відтворюється без three.js, у Chrome/Edge, у Firefox і Safari приклад працює; мейнтейнер завів запис у трекері Chromium (1472979). Issue закрито 2023-10-26; у гілці запропоновано обхідний PR #27017 (чи саме він її закрив, з коментарів не видно). [П]
- Відкрита проблема #26950 (2023-10): CSS-трансформації «дуже крихкі» до умов DOM-контейнера і різні в кожному браузері. [П]
- Safari на iPhone X: зсув CSS-шару відносно WebGL на HiDPI (#19854, закрито 2021-03-03); мобільна помилка позиції #15089 (2018, закрито). [П]
- **Iframe і походження (origin).** Сторінка в iframe тієї ж адреси, що й сцена, може взаємодіяти зі сценою скриптом. Наш сервер не шле `X-Frame-Options`, тож iframe не блокується. [П, код сервера + приклад css3d_mixed]. Щоб сцена three.js могла робити `fetch('/state')`, її файли має віддавати **той самий сервер** (інакше потрібні CORS-заголовки, яких у сервері немає): це змінює код сервера. [Ч, мій висновок; у цьому завданні код не змінювався]
- **Шрифти.** Пульт використовує системний `Segoe UI`, на телефоні буде інший шрифт. Для варіанта з SVG-текстурою будь-які зовнішні шрифти й картинки треба вбудовувати всередину SVG (обмеження `foreignObject`, загальне правило). [Ч]

### Телефон без встановлення

- three.js/WebGL відкривається в мобільному браузері без встановлення (загальновідомо, окремо не перевіряв). [Ч] Але **сервер зараз слухає лише 127.0.0.1**, тому з телефона він недосяжний: потрібен 0.0.0.0 або хостинг, обидва змінюють код/конфіг сервера. [П для факту 127.0.0.1]
- Якщо сцену виставити на публічний HTTPS, а `/state` лишається на локальній адресі, Chrome 142+ показує запит дозволу «Local Network Access» на запити з публічного сайту до локальної мережі/loopback; змішаний вміст для запитів до IP-літерала приватної мережі виключається з перевірок mixed content. [П, developer.chrome.com/blog/local-network-access] Для варіанта «локальний сервер віддає і сцену, і `/state`» це не діє. [Ч]
- Дотик у iframe у CSS3D на телефоні, скрол і жести поверх камери **не перевірялись, джерел не знайдено**.

## 6. Найменш ризикований шлях для пілоту (пункт 5)

### Рекомендація

**Пілот у Unity 6.3 LTS з Vuplex 3D WebView for Windows** (спочатку 14-денний триал, потім $160–180 за місце), графічний API DX11, сцена: кімната, монітор із `WebViewPrefab`, одна норія, що читає `/state`.

Чому саме так:

1. Це єдиний з розглянутих шляхів, де «веб-сторінка на 3D-поверхні з кліком і клавіатурою» є **підтримуваним комерційним продуктом**, а не обхідним прийомом: актуальна версія (4.15.2, 2026-06-12), Chromium 137, документований `WebViewPrefab`, замінний детектор вказівника, окремо зазначено, що обмеження щодо `<select>` і `title` **не стосуються** Windows-версії. Ціна відома до купівлі, триал безкоштовний.
2. Unreal найгірший саме в цьому місці: вбудований браузер на Windows тримається на Chromium 90 (до 5.6 підтверджено, для 5.8 невідомо), віджет експериментальний, ввід через WIC для клавіатури зламаний за свіжим повідомленням 2026-01, а цикл браузера типово 15 Гц. Обхід (BLUI) існує й живий, але це ще одна залежність від одного автора.
3. Godot безкоштовний і заявляє те саме, але молодий проєкт має відкриті помилки синхронізації GPU/джитера саме на Windows; для пілоту, де рішення про рушій ще не прийнято, це ризик «застрягти на баг рушія-обгортки».
4. three.js має найнижчий ризик **лише для монітора** (офіційний приклад), але він не відповідає на питання про рушій, а масштаб сцени (55 тис. дерев, ~167 млн граней у не оптимізованому вигляді) там теж треба спрощувати вручну.

Це судження за документацією; **у живому проєкті я нічого з цього не запускав.** Судити про придатність можна лише після приймальних тестів нижче.

### Приймальні тести пілоту (у порядку відсіву)

1. Клік по кнопці «Пуск/Стоп» у пульті з 3D-курсору доходить до `POST /cmd` (видно в журналі пульта) і 3D-норія змінює стан за `/state`.
2. `<select id="scenario">` відкривається і вибір спрацьовує.
3. У поле `#feed` можна ввести цифри з реальної клавіатури, коли гравець «сидить за монітором».
4. Текст 13 px читабельний на моніторі з роздільністю вмісту 1920×1080 при типовій відстані камери.
5. Кадри сцени не падають нижче задуманого порога, коли пульт відкритий (пульт оновлюється лише 4 Гц).
6. Зібраний exe працює на «чистій» Windows-машині без редактора; локальний сервер симулятора запускається окремо (рушій його не хостить).

### Що робити, якщо плагін не підходить

Запасний варіант: **нативний пульт на UI рушія**, що читає той самий `/state` і шле той самий `POST /cmd`. Обсяг відомий: 42 вузли й 59 ребер у `layout.json`, ≈15 КБ логіки `panel.js`. [П, код]

- **Unity:** UnityWebRequest + Newtonsoft-json для словників за id [П]; SVG-мнемосхему `/mnemo.svg` можна імпортувати: у Unity 6.3 вбудований модуль Vector Graphics імпортує SVG для UI Toolkit і Texture2D, а пакет `com.unity.vectorgraphics` (3.0.0-preview) потрібен лише для Sprite/uGUI `SVGImage`; пакет лишається у статусі preview [П, підсумок пошуковика за документацією Unity 6.3; сторінку не відкривав]. Але вона статична: розфарбувати елементи за `id` під час гри потребує власного коду. [Ч]
- **Unreal:** модулі `HTTP` і `Json` вбудовані, у Blueprint є плагін VaRest(X) [П]. UMG не має нативного SVG; є сторонні плагіни (UMG SVG на Fab, SvgBooga MIT) [П]. Чистіший шлях: будувати мнемосхему з `layout.json` віджетами. [Ч]
- Розумна межа: у нативному варіанті ділиться джерело правди (`/state`, `/cmd`, `layout.json`), а **малювання дублюється**. Кожна зміна `panel.js` робиться двічі.
- Варіант «захопити вікно браузера як текстуру» (`window capture`, Spout/NDI) я **не досліджував**. Клік для нього довелося б передавати як події ОС, що виглядає крихким. [Ч]

## 7. Blender → рушій (пункт 6, орієнтовно, без строків)

Що є в сцені (з коду `world/kit`, прочитано [П]): дерева це **колекційні екземпляри** трьох прототипів (у кожного стовбур + крона окремими мешами) з позиціями від `landscape.tree_positions(site)` (детермінований, з `SITE.json`); матеріали процедурні (`ShaderNodeTexNoise`, `TexVoronoi`, `TexWhiteNoise` у `world/kit/common.py`); нічне світло на лампах Blender з IES (`lighting.py`, Cycles).

| Що | Що станеться | Що робити (мій висновок, крім позначених [П]) |
|---|---|---|
| **Формат** | glTF 2.0 рекомендований для Godot (`.blend` імпортується через прозорий експорт glTF, потрібен встановлений Blender) [П]; Unreal імпортує glTF; FBX теж; є додаток Epic/спільноти Send to Unreal (меші, скелети, анімація; про матеріали в описі нічого) [П] | glTF для статичної геометрії; FBX лише якщо знадобиться скелет |
| **Процедурні матеріали** | Експортер glTF Blender (мануал 4.5) читає Base Color з входу Principled BSDF, картинки (Image Texture), RGB чи AO; про процедурні вузли (Noise/Voronoi) у мануалі нічого, тож у glTF вони не потраплять [П для переліку, висновок Ч] | **Запікати** у картинки (Base Color, Roughness, Normal), металік/шорсткість з рекомендованим пакуванням каналів; тайлові текстури для великих поверхонь (земля, бетон) |
| **55 тис. дерев** | Колекційні екземпляри експортер GPU-інстансів не візьме як є: вимоги мануала 4.5: екземпляри мають бути **мешами без дочірніх**, **дітьми одного об'єкта**, спільна mesh-data, **без варіацій матеріалу**. Unity glTFast підтримує `EXT_mesh_gpu_instancing`; на сторінці Epic про glTF у списку розширень його немає (там 6 розширень KHR, сторінка описує експорт), для імпорту в Interchange **не знайдено** [П] | Не тягти дерева через glTF. Експортувати **лише позиції** (JSON/CSV із `tree_positions`) і три прототипи, а в рушії розставити інстансами: Unity GPU Resident Drawer (потрібні Forward+/Deferred+, GameObject без MaterialPropertyBlock) [П]; Unreal ISM/HISM (Nanite Foliage у 5.8 має статус Experimental «use caution when shipping» [П]); Godot MultiMesh із visibility range [Ч, блог] |
| **Світло** | glTF знає лише `KHR_lights_punctual` (точкове, прожектор, напрямлене) [П для Unreal-списку]. **IES** не переноситься. Unreal підтримує IES для точкових/прожекторів/rect-світла [П]; для Unity знайдено лише PR IES у репозиторії Graphics [Ч]; у Godot запит на IES відкритий з 2025-01 [П] | Нічні лампи налаштувати в рушії заново; IES-файли лежать окремо |
| **Запечене світло** | Запечений у Blender lightmap як освітлення не переноситься: рушії воліють власні бейкери; в Unity потрібен другий UV-канал (`uv2`) [П]; у Unreal форум 2015 (UE4): «рушій це не підтримує», обхід через Emissive [П, стара стаття, для 5.x перевірки не знайшов] | Освітлення переробити в рушії (Lumen / Unity APV або бейк). З Blender брати геометрію й запечені albedo/AO |
| **Масштаб** | 167 млн граней дерев у Blender (140 мс/кадр із деревами проти 6 мс без них) [П, повідомлення коміту 19a780c «Control center stage 0»] | Прототипи дерев спростити до LOD; для пілоту дерев не треба взагалі |

Орієнтовна величина роботи (без строків): найдорожче це запікання матеріалів і переробка світла; найдешевше експорт статичної геометрії; для пілоту (кімната, монітор, одна норія) дерева, ІES і lightmap можна не переносити.

## 8. Що лишилось невідомим

1. Чи вбудований Web Browser в **UE 5.8** на Windows типово використовує CEF 128 і чи стабільний (у 5.6.1 вмикання прапора крашило). Офіційних нотаток не знайдено.
2. Умови ліцензії Unreal для інтерактивного проєкту, що не є грою (сторінки Epic віддали 403).
3. Поведінка Vuplex у першій особі з нашим `#feed`, `<select>` і підказками: за документацією має працювати, **не випробувано**.
4. Точне дослівне формулювання ліцензії Vuplex (сторінка завантажується скриптом): «ліцензія на розробника» взято зі зведення та рядка в Asset Store.
5. godot-cef: як саме передавати введення в 3D (документація мовчить).
6. Сенсорне керування iframe у CSS3D на телефоні.
7. Реальна вартість CPU/GPU одного браузера з пультом (4 Гц) у кожному рушії: не вимірювалась.
8. Чи потрапляє Unity 6.6 / 6.7 LTS у плани (лише вторинне джерело).

## 9. Джерела

Дата перевірки всіх сторінок: 2026-09-29. У дужках дата матеріалу, якщо вона видна.

Код проєкту (читання)
- `D:\autocad project\world\sim\server.py`, `world\panel\{index.html,panel.js,panel.css,layout.json}`, `world\sim\STATE_SCHEMA.json`, `world\kit\landscape.py`, `world\kit\common.py`, `world\kit\lighting.py`

Unreal
- https://forums.unrealengine.com/t/request-for-guidance-on-updating-cef-in-unreal-webbrowser-plugin/2617726 (2025-06-20…2025-11-25, читано через `.json`; відповіді співробітників Epic 2025-06-23/24/25)
- https://forums.unrealengine.com/t/windows-supported-for-cef-128-4-shipped-with-unreal-5-6-1/2657521 (2025-09-17…11-11)
- https://forums.unrealengine.com/t/web-browser-super-low-fps/467552 (2020-07-02…2026-08-27)
- https://forums.unrealengine.com/t/web-browser-widget-in-3d-using-widgetcomponent-scales-unexpectedly-on-android/1848077 (2024-05-09)
- https://forums.unrealengine.com/t/web-browser-widget-not-working-with-widget-interaction-component-in-vr/418018 (2018-02…2019-10)
- https://forums.unrealengine.com/t/ue5-5-keyboard-input-issue-with-3d-widget-widget-component-using-widget-interaction-component/2689070 (2026-01-02)
- https://forums.unrealengine.com/t/typing-in-3d-widget/369550 (2016-09…2021-06)
- https://forums.unrealengine.com/t/web-browser-widget-picture-blurry/364853 (2016-07…2017-09)
- https://forums.unrealengine.com/t/unreal-engine-5-7-released/2673913 (реліз 5.7: 2025-11-12; нотатки патчів 5.7.1–5.7.4)
- https://forums.unrealengine.com/t/import-baked-lightmap-into-unreal-engine/45706 (2015-10, UE4)
- https://dev.epicgames.com/documentation/en-us/unreal-engine/API/Plugins/WebBrowserWidget/UWebBrowser (UE 5.8)
- https://dev.epicgames.com/documentation/en-us/unreal-engine/widget-components-in-unreal-engine (UE 5.8)
- https://dev.epicgames.com/documentation/en-us/unreal-engine/creating-3d-widget-interaction?application_version=4.27 (UE 4.27)
- https://dev.epicgames.com/documentation/en-us/unreal-engine/gltf-file-format-support-in-unreal-engine (UE 5.8)
- https://dev.epicgames.com/documentation/en-us/unreal-engine/nanite-foliage (UE 5.8)
- https://dev.epicgames.com/documentation/en-us/unreal-engine/using-ies-light-profiles-in-unreal-engine
- https://dev.epicgames.com/documentation/en-us/unreal-engine/unreal-engine-5-8-release-notes
- https://unrealcommunity.wiki/web-browser-widget-13f406 (~2021, CEF 59, категорія Experimental)
- https://docs.unrealengine.com/4.26/en-US/API/Plugins/WebBrowserWidget/UWebBrowser/GetPaletteCategory/ (4.26)
- https://www.cgchannel.com/2026/06/see-5-key-features-for-cg-artists-in-unreal-engine-5-8/ (2026-06-17)
- https://github.com/getnamo/BLUI-Unreal (v5.1.0 для UE 5.8: 2026-09-25)
- https://github.com/ArtemIyX/WebUserInterfaceUnreal
- https://alienmelon.itch.io/bluesuburbia/devlog/621860/packaging-your-game-with-and-locally-loading-bitsy-in-unreal-or-pocket-platformer-or-decker-or-any-other-html-project (~2021, UE 4.26)
- https://epicgames.github.io/BlenderTools/send2ue/

Unity
- https://store.vuplex.com/webview/windows-mac/ (сирий HTML)
- https://developer.vuplex.com/webview/overview
- https://developer.vuplex.com/webview/WebViewPrefab
- https://developer.vuplex.com/webview/StandaloneWebView
- https://support.vuplex.com/articles/3d-rendering-limitations/ (оновлено 2024-06-06)
- https://store.vuplex.com/free-trials/?product=Unity.WebView.Standalone
- https://assetstore.unity.com/packages/tools/gui/3d-webview-for-windows-and-macos-web-browser-154144
- https://developer.vuplex.com/commercial-library-license (порожня оболонка, змісту не бачив)
- https://unity.com/releases/unity-6/support
- https://unity.com/products/pricing-updates
- https://www.cgchannel.com/2025/11/price-of-paid-unity-subscriptions-to-rise-but-free-subs-extended/
- https://makaka.org/unity-tutorials/best-version (2026-09-18, вторинне)
- https://github.com/gree/unity-webview
- https://github.com/Voltstro-Studios/UnityWebBrowser
- https://docs.unity3d.com/Packages/com.unity.cloud.gltfast@6.7/manual/features.html
- https://docs.unity3d.com/6000.0/Documentation/Manual/urp/gpu-resident-drawer.html (через пошук; вимоги Forward+)
- https://discussions.unity.com/t/jsonutility-cant-serialize-dictionary/833773 та https://docs.unity3d.com/Packages/com.unity.nuget.newtonsoft-json@3.0/manual/index.html
- https://docs.unity3d.com/6000.3/Documentation/Manual/ui-systems/work-with-vector-graphics.html (через пошук)

Godot
- https://godotengine.org/download/archive/ (4.7.2: 2026-08-18)
- https://github.com/dsh0416/godot-cef (README, GitHub API: створено 2025-12-31, push 2026-09-27; issues #193, #227, #181, #207, #162)
- https://github.com/Lecrapouille/gdcef (v0.20.0: 2026-08-20; issue #62)
- https://github.com/godotengine/godot-demo-projects/tree/master/viewport/gui_in_3d
- https://godotcef.org/api/
- https://github.com/godotengine/godot-proposals/issues/715 (IES, відкрито)
- https://docs.godotengine.org/en/stable/tutorials/assets_pipeline/importing_3d_scenes/available_formats.html

three.js / веб
- https://raw.githubusercontent.com/mrdoob/three.js/dev/examples/css3d_youtube.html і https://raw.githubusercontent.com/mrdoob/three.js/dev/examples/css3d_mixed.html (сирий код, three.js r186, 2026-09-24)
- https://threejs.org/docs/pages/CSS3DRenderer.html
- https://github.com/mrdoob/three.js/issues/26583, /26950, /19854, /15089
- https://discourse.threejs.org/t/interactive-screen-inside-a-3d-model/66069 та https://discourse.threejs.org/t/iframe-inside-mesh/66626
- https://github.com/repalash/three-html-render
- https://developer.chrome.com/blog/local-network-access

Blender / перенесення
- https://docs.blender.org/manual/en/4.5/addons/import_export/scene_gltf2.html (розділи GPU Instances, Materials, Extensions; для `latest` сторінка віддає 404)
- https://docs.unity3d.com/Manual/LightingGiUvs-GeneratingLightmappingUVs.html (через пошук)
- https://github.com/Unity-Technologies/Graphics/pull/459 (IES, через пошук)
- https://www.strayspark.studio/blog/blender-5-to-unreal-engine-57-asset-pipeline-2026 (маркетинговий блог, лише як натяк [Ч])
