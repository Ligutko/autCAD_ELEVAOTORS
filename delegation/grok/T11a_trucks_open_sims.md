# Завдання T11a: реалістичні європейські вантажівки з відкритих симуляторів і відкритих репозиторіїв (без логіну)

Робоча папка: `D:\autocad_grok_wt\t11-trucks-sim`. Ліміт: 25 хвилин, 50 викликів. Мова: українська.

## Контекст
На Sketchfab безкоштовних моделей не знайшлося (перевірено людиною), попередній пошук без логіну дав лише іграшкові low-poly (`research/design/people_trucks/nologin_assets.md` у гілці grok/t9-people-trucks). Потрібні **реалістичні** моделі вантажного тягача / самоскида / зерновоза, придатні для кадру поруч із силосами, з ліцензією, що дозволяє комерційне використання (MIT, Apache-2.0, CC0, CC-BY), скачувані прямим HTTP без облікового запису.

## Де шукати (перевір ліцензію саме ассетів, не тільки коду)
- CARLA simulator (vehicle.carlamotors.european_hgv, firetruck, carlacola тощо): ліцензія контенту CARLA (CC-BY?) і чи є вихідні FBX/OBJ поза .uasset (репо carla-content, «CARLA assets source»);
- LGSVL/SVL simulator, AirSim, BeamNG (не підходить, якщо закрита ліцензія), Godot/Bevy demo assets, Open 3D Engine (O3DE) assets, Unity/Unreal безкоштовні зразки з відкритою ліцензією, NVIDIA Isaac/Omniverse sample assets (перевір ліцензію), OpenStreetMap-проєкти (OSM2World) моделі транспорту;
- GitHub пошук: "semi truck glb", "tractor trailer fbx license CC0", "dump truck gltf CC-BY".

## Що робити
- Скачуй лише файли без логіну, ≤ 100 МБ, у `research/design/people_trucks/sim_trucks/<назва>/` з `LICENSE.txt` (точний текст або посилання на ліцензію саме ассетів) і `SOURCE.txt`.
- Якщо модель лише у .uasset/.umap, не качай, опиши.
- Для кожного: формат, розмір, SHA-256, трикутники якщо відомо, окремі колеса / кузов.

## Звіт
`research/design/people_trucks/sim_trucks/README.md`: таблиця, чесний висновок «реалістично / іграшково», чого не знайдено. Нічого поза цією папкою не змінюй. Не реєструйся, ключів не вводь. Наприкінці 8 рядків підсумку.
