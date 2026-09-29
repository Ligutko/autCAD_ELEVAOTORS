# Кандидати: безкоштовні 3D-фури для сцени розвантаження

Дата пошуку: 2026-09-29. Лише пошук. У Blender нічого не імпортовано. Файлів моделей не скачано: у кандидата №1 немає прямого завантаження без облікового запису, тож SHA-256 немає.

Жодного готового комплекту «впізнаваний європейський тягач + самоскидний напівпричіп-зерновоз або зерновоз із рухомою підлогою» з явною комерційною ліцензією і прямим завантаженням без реєстрації не знайдено. Нижче окремо тягачі, окремо кузови й один риг.

Полігони Sketchfab — це поле `faceCount` публічного API `https://api.sketchfab.com/v3/models/{uid}` (трикутники). Розмір архіву і вихідний формат цей API без токена не віддає. Запит `GET /v3/models/59889032d0ad457c81d7e058c79eedf8/download` повернув **HTTP 401**.

## Таблиця

| # | Назва | Марка / модель | URL | Автор | Ліцензія (текст і посилання) | Комерція | Формат | Полігони | Без реєстрації | Окремі колеса і кузов | Текстури | Розмір |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | DAF XF 105 - Truck | DAF XF 105 Space Cab і вигаданий причіп (не зерновоз) | https://blendswap.com/blend/17233 | Kartoffelphantom | На картці: `CC-BY`. Сторінка завантаження показує: «Free under CC-BY. Please credit Kartoffelphantom when you use it.» Версію CC (3.0 чи 4.0) картка не називає. Посилання «Read the full license» є, тіло ліцензії без логіну не відкрив | так, з атрибуцією; версію CC перевірити руками | blend (Blender 2.7x, Blender Internal) | не вказано; автор пише lowpoly | ні. Картка: завантаження після входу. Спроба прямого URL у цьому сеансі до файлу не дійшла | не вказано | так, запаковані. У коментарі baldyman_1248537: матеріал `DAF_XF`, файл `DAF_XS.dds` у External Data | 398 KB |
| 2 | Scania truck | Scania, конкретна серія в описі не названа | https://sketchfab.com/3d-models/scania-truck-59889032d0ad457c81d7e058c79eedf8 | PAndras (акаунт PusztaiAndras) | Sketchfab: «CC Attribution», «Creative Commons Attribution», вимоги API: «Author must be credited. Commercial use is allowed.» Deed CC BY 4.0: «Share — copy and redistribute the material in any medium or format for any purpose, even commercially.» «Adapt — remix, transform, and build upon the material for any purpose, even commercially.» «Attribution — You must give appropriate credit, provide a link to the license, and indicate if changes were made.» http://creativecommons.org/licenses/by/4.0/ | так | не вказано публічним API | 249084 трикутники, 128503 вершини | ні (download API: 401) | не вказано. Анімацій у API: 0 | не вказано | не вказано |
| 3 | Mercedes-Benz Actros Tipper 3axis 2011 | Mercedes-Benz Actros, тривісний самоскид (жорсткий, не напівпричіп) | https://sketchfab.com/3d-models/mercedes-benz-actros-tipper-3axis-2011-f0ea60be9d84488496d568a9919cb044 | Nieve5677 (акаунт niev) | Той самий CC BY 4.0, що в рядку 2. API: «Author must be credited. Commercial use is allowed.» http://creativecommons.org/licenses/by/4.0/ | так | не вказано публічним API | 1619582 трикутники, 822101 вершина | ні (той самий механізм Sketchfab, 401 на download) | не вказано. Анімацій: 0. Опис автора: «2000th Model!» | не вказано | не вказано |
| 4 | Tipper Trailer | марка не вказана, самоскидний причіп | https://sketchfab.com/3d-models/tipper-trailer-2005ecb316c24f20a0c774062fe06d70 | Dead_Pixels | Той самий CC BY 4.0. API: «Author must be credited. Commercial use is allowed.» http://creativecommons.org/licenses/by/4.0/ | так | не вказано публічним API | 1135001 трикутник, 728701 вершина | ні | не вказано. Опису немає | не вказано | не вказано |
| 5 | Scania truck semi trailer | Scania і напівпричіп; тип кузова в описі не названий | https://sketchfab.com/3d-models/scania-truck-semi-trailer-303ff150ea9b4a90bec60930e36da6d4 | zairiq zairiq (акаунт zairiqzairiq) | Той самий CC BY 4.0. API: «Author must be credited. Commercial use is allowed.» http://creativecommons.org/licenses/by/4.0/ | так | не вказано публічним API | 169371 трикутник, 97327 вершин | ні | не вказано. Опису немає | не вказано | не вказано |
| 6 | Volvo FH 460 - RICK MODDING | Volvo FH 460 | https://sketchfab.com/3d-models/volvo-fh-460-rick-modding-dcd13ab86e1e469d9daa83d4cbca669e | Rick_modding (акаунт Rick_modding_) | Той самий CC BY 4.0. API: «Author must be credited. Commercial use is allowed.» http://creativecommons.org/licenses/by/4.0/ | так | не вказано публічним API | 1072958 трикутників, 565092 вершини | ні | не вказано. Анімацій: 0. Теги: truck, volvo-trucks, volvofh | не вказано | не вказано |
| 7 | Tractor Trailer with Rig | збірний американський тягач із фургоном, не зерновоз і не європейська марка | https://blendswap.com/blend/20912 | ThePefDispenser | На картці: `CC0`. Deed CC0 1.0: «The person who associated a work with this deed has dedicated the work to the public domain by waiving all of his or her rights to the work worldwide under copyright law, including all related and neighboring rights, to the extent allowed by law.» «You can copy, modify, distribute and perform the work, even for commercial purposes, all without asking permission.» Там само: торговельні марки CC0 не передає. https://creativecommons.org/publicdomain/zero/1.0/ | так | blend (Blender 2.7x, Cycles) | не вказано. Автор: після Apply дзеркал база висока, subsurf знятий не скрізь | ні, BlendSwap просить акаунт | так для ригу: передні колеса повертаються, двері відчиняються, задні бризковики на кривих. Салон порожній | не описані окремо | 9.6 MB |
| 8 | Low-poly tipper truck | без марки, стилізований самоскид | https://www.blendkit.com/asset-gallery-detail/f93edb13-0581-4129-bc29-cb4439744e8f/ | imiserygoat | Blendkit Royalty Free, цитата зі сторінки ліцензій: «This license protects the work in the way that it allows commercial use without mentioning the author, but doesn't allow for re-sale of the asset in the same form (eg. a 3D model sold as a 3D model or part of assetpack or game level on a marketplace).» Загальне правило сайту: «Everything you download is available for commercial use.» https://www.blendkit.com/docs/licenses/ | так, але саму модель перепродавати не можна | blend через Blendkit; точний контейнер файлу не бачив | 1838 | ні. Картка безкоштовна (Free), файл без акаунта Blendkit не віддає | не вказано. Опис: «low-poly tipper truck with distortion geometry» | не вказано | 133.2 KiB |

Окремо, не в трійці: Peferbuilt Tractor Trailer, ThePefDispenser, CC-BY, https://blendswap.com/blend/19634. Автор пише, що деталі названі, колеса — instanced groups, кабіна є parent усього зчепа. Розмір файлу на відкритій картці не побачив. Це сухий американський тягач, не зерновоз. Завантаження теж лише після входу.

## Три найкращі

1. **DAF XF 105 - Truck (BlendSwap).** Це єдиний маленький рідній `.blend` впізнаванної європейської кабіни (DAF XF 105 Space Cab) разом із причепом, під CC-BY, 398 KB, з запакованою текстурою `DAF_XS.dds`. Причіп автор прямо називає вигаданим, тож це не зерновоз: кузов для ями доведеться міняти або брати з рядка 3 чи 4. Колеса як окремі об'єкти автор не описує, і файл без акаунта BlendSwap не віддається.

2. **Scania truck (PAndras, Sketchfab).** Найпопулярніша з перевірених вільних Scanіа: CC BY 4.0 прямо дозволяє комерційне використання за атрибуції, 249 тис. трикутників — середня вага для реквізиту. Серію, окремі колеса, текстури і розмір архіву публічне API не показує, завантаження без логіну закрите (401). Чи це чистий тягач без причепа, зі сторінки не видно.

3. **Mercedes-Benz Actros Tipper 3axis 2011 (Sketchfab).** Єдиний перевірений CC BY 4.0 модель саме самоскидного кузова на впізнаванній європейській марці. Це тривісний жорсткий самоскид, не напівпричіп-зерновоз, 1,62 млн трикутників і нуль анімацій у API, тож підйом кузова доведеться ригати самим. Походження сітки автор не доводить.

Ригований CC0 `Tractor Trailer with Rig` чистіший юридично (публічний домен, колеса вже крутяться), але це американський фургон, не європейський зерновоз. Для ями він годиться як донор ригу, не як фінальний реквізит.

## Чесно про пошук

Скачати кандидата №1 не зміг. BlendSwap на картці DAF вимагає вхід. Sketchfab download API без токена відповідає 401. Реєстрацію не створював, ключів не вводив. Файла в `research/design/trucks/candidates/` немає, SHA-256 немає.

Зерновоза з рухомою підлогою (walking floor) під CC-BY або CC0 у пошуку Sketchfab не було: запит `walking floor trailer` з фільтром downloadable + CC-BY повернув порожній список. Окремого безкоштовного напівпричепа-зерновоза з названою маркою кузова теж немає. `Tipper Trailer` Dead_Pixels і Actros Tipper — найближчі кузови, але перший без опису і дуже важкий, другий не напівпричіп.

Сумнівні ліцензії, які в таблицю не ставив:

- **Caminhão Volvo FH 750**, Matheus.Molina, бейдж CC BY 4.0, 1,26 млн трикутників, https://sketchfab.com/3d-models/caminhao-volvo-fh-750-314f957331344efcb574b35da7bba99f. В описі автор пише, що модель витягнута з гри Truck Simulator і потім відполірована. Моди Euro Truck не брав. Бейдж CC-BY не скасовує чужий ігровий ассет.
- **MAN TGX 2010** (tonielpro520, 34748 трикутників) і **MAN TGX 2010 V8** (DevPoly3D, 37692 трикутники) теж мають бейдж CC BY 4.0, але виглядають як ігрові кабіни з чужих рендерів у описі. Право автора ставити CC-BY я не перевірив. У трійку не ставив.
- **SCANIA S730 V8 - RICK MODDING** (Rick_modding, CC BY 4.0, 2,25 млн трикутників) — та сама невизначеність походження, плюс заважка для сцени.
- **CGTrader, Tipper Truck 3D Rigged Model**, https://www.cgtrader.com/free-3d-models/vehicle/truck/tipper-truck-3d-rigged-model. Бейдж сторінки: `Royalty Free License (no AI)`, кнопка Free Download. Текст автора: «License Info: Free to use for educational and personal purposes. Not for commercial resale or redistribution.» Комерція: **не зрозуміло**. Формати на сторінці: OBJ 5.68 MB, Maya 2022 (Arnold) 37.6 MB, FBX 18 MB, PNG 32.9 MB. Риг Maya. Без логіну не качав.
- **Blendkit Scania R500 Truck**, AmJViZ, https://www.blendkit.com/asset-gallery-detail/8d502b9c-09f1-4490-a10a-4bd7174ed8e7/ : 554092 полігони, 82.0 MiB, Royalty Free, у комплекті з причепом за описом, але картка позначена **Full Plan**, тобто платна. Безкоштовною її не рахував. Поруч так само платні Scania R450, Mercedes Actros Box, Mercedes Antos Semi, Dump Truck.
- **TurboSquid і Free3D.** Відкриті картки зерновозів і самоскидних причепів були платні (Free3D Tipper Trailer близько $29, «Royalty Free License Editorial Only»; TurboSquid Agricultural Tipper Trailer $59, Dump Trailer $59–$99). Сторінка TurboSquid обіцяє безкоштовні semi-trailer truck, конкретну безкоштовну модель зерновоза з комерційною ліцензією я не відкрив.
- **Poly Pizza.** Є стилізовані CC0 (Quaternius Truck, https://poly.pizza/m/cXw6oiFtZ8) і CC-BY самоскид (Crachboss32, https://poly.pizza/m/gYWUCpb09B, автор пише додати колеса самому). Це не впізнаванні Scania, DAF, MAN, Volvo, Mercedes чи Iveco.
- **GitHub.** Репозиторії модів Euro Truck Simulator не розбирав. Моделі esmini (`semi_tractor`, `semi_trailer`) лише побачив у каталозі; ліцензію самих мешів не читав, у кандидати не ставив.

Що перевірити руками перед тим, як класти модель у сцену:

- Відкрити blend DAF і обидві Sketchfab-моделі трійки й подивитися, чи колеса, кабіна і кузов є окремими об'єктами. Ззовні цього не видно.
- Звірити масштаб із ямою (метри, не «одиниці файлу»).
- Переконатися, що автор сітки справді мав право ставити CC-BY. Бейдж Sketchfab цього не доводить. Особливо Rick_modding, tonielpro520, DevPoly3D і будь-який опис зі словами Truck Simulator.
- Торговельні марки. Deed CC0 прямо каже, що trademark rights не зачіпаються. CC BY теж дає лише авторське право на модель. Логотипи Scania, DAF, Volvo, Mercedes на борту — окреме питання, його ця добірка не закриває.
- Версію CC-BY на BlendSwap: картка пише лише `CC-BY`, без номера. Повна сторінка ліцензії відкривається після входу.
- Чи якість Tipper Trailer (1,1 млн трикутників, порожній опис) — це модель, чи важкий скан.

Сайти, куди не ходив за умовою завдання: grabcad.com, traceparts.com.
