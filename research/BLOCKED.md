# Заблоковані домени

Дата: 2026-09-24
Середовище: хмарний контейнер Claude Code з egress-проксі.
Перевірка: `curl https://<домен>/` повертав `CONNECT tunnel failed, response 403`, WebFetch — `EGRESS_BLOCKED`. Обходити не пробував.

Відкривалися тільки `github.com`, `api.github.com` (через MCP), `raw.githubusercontent.com`, `gitlab.com`, `pypi.org`, `files.pythonhosted.org`. Пошук (WebSearch) працював: він показує уривки сторінок, але не відкриває файлів.

| Домен | Що хотів узяти |
|---|---|
| lubnymash.com | паспорт і креслення норії У13-УН-100, опитувальний лист МСВУ з розмірами люків, аерації і термометрії (частина PDF уже лежить у `inbox/raw/web/_fetch/`) |
| www.go4b.com, go4b.co.uk | 4B: каталог ковшів (Starco, CC-S, Jumbo), `euro-elevator-bolts.pdf` (DIN 15237), `ad-din-elevator-buckets.pdf`, інструкції Touchswitch, M800, Whirligig, `bucket-elevator-monitoring.pdf` |
| www.jealco.com, jealcostore.com | повна таблиця Tapco CC-HD (12x7: габарити, WL-місткість, маса, отвори) |
| www.tapcoinc.com | каталог Tapco, `Tapco_2008_Catalog_95.pdf` (розрахунок продуктивності) |
| rossmfgco.com | таблиці місткості Tapco CC-HD і CC-XD |
| maxilift.com | таблиця Tiger-Tuff і HD-Max |
| meganorm.ru, docs.cntd.ru, files.stroyinf.ru | текст ГОСТ 4596-75 (ковші норій), СН 302-65 |
| www.ntf-gummi.de, www.indutechnik.com, www.mullerbeltex.com, www.hedfeld.com, www.aschauer.com, products.pewag.com | таблиці DIN 15231–15234 (ковші) і DIN 15237 (болти) |
| www.skf.com, skf.partcommunity.com, www.3dfindit.com | каталог SNL (є копія на GitHub), STEP-моделі SNL |
| www.timken.com, cad.timken.com, catalog.amibearings.com, www.fyh.co.jp, www.ntn.co.jp | креслення і STEP UCP211 |
| www.bonfiglioli.com, www.nord.com, www.sew-eurodrive.de, dodgeindustrial.com, baleromex.com | габарити насадних редукторів на 22 кВт (TA, SK…AZ, SA, TXT) |
| cemcomo.com, library.e.abb.com, www.jameselectric.ca, lewismotorrepair.com | таблиці IEC 60072 для габариту 180 (A, B, C, K, D, E) |
| agri.chiefind.com | Chief Elevator Design Guide (таблиця барабан/ківш/крок/труба); інструкції даху CB26 (навантаження термокабелів) |
| www.brockgrain.com | `Brock-Bucket-Elevator-Capacities-Dimensions` (габарити труб і голів) |
| dam.buhlergroup.com | data sheet Bühler LBEB (барабани, стрічка, продуктивність, габарити) |
| www.agm-nr.sk, pdf.agriexpo.online | Petkus BE 130/180/280, BE 370/660/900 (розміри голів і башмаків) |
| www.andritz.com | datasheet BE50–BE700 |
| www.kwsmfg.com | CEMA-розміри норій (dimensional standards) |
| www.cemanet.org | CEMA Bucket Elevator Book, розділ 6 «Buckets» |
| www.nfpa.org, docinfofiles.nfpa.org, atapars.com | текст NFPA 61 (розрядники, датчики) |
| www.pcimfg.com | геометрія крильчастих барабанів (кількість і товщина крил) |
| knowledge.opisystems.com, opisystems.com | схеми розстановки кабелів OPI за діаметрами до 105 ft |
| www.grainsystems.com | `pneg1924` (GSI: термокабелі в бункерах 54–135 ft), інструкції з анкерами 40-series |
| www.world-grain.com | статті про розстановку термокабелів (використано уривки) |
| www.agrolog.io | datasheet SL3000/5000 |
| www.symaga.com | SBH (канали аерації), технічні дані аксесуарів (люки, двері, драбини), датчики рівня |
| www.aggrowth.com, www.framespa.com | AGI FRAME: двері силосів, вентилятори, датчики |
| www.riela.pl, www.mysilo.com, www.simeza.com | аерація і анкери плоскодонних силосів |
| vniiz.org | статті ВНІІЗ про вентилювання силосів 1000–10 000 т |
| kmzindustries.ua, tender.kernel.ua | зачисні шнеки (ШЗС-400) |
| neuero-ukraina.com.ua | силос NL 22/24: термозонди, вентилятори |
| extension.okstate.edu | BAE-1102 «Aeration Systems for Flat-Bottom Round Bins» (схеми каналів) |
| grabcad.com, www.traceparts.com, www.3dcontentcentral.com, www.cgtrader.com, www.bibliocad.com | CAD-моделі (див. `CAD_SOURCES.md`) |
| rusbelt.ru, prome-tech.ru, beltprofi.ru, zerteh.ru | картки ковшів УКЗ і МАСТУ з місткістю |
| en.wikipedia.org, uk.wikipedia.org | загальні довідки |
| archive.org, researchgate.net, sciencedirect.com, zenodo.org | архівні копії PDF і статті (сили на термокабелях) |
| www.metallum.com.ua, dinmark.com.ua, krepcom.ru, gost-din.ru | вибухорозрядники норій (розміри мембран); таблиця DIN 15237 повністю |
