# WEBtrade - Kereskedős-játék állomások online implementációja

A [kereskedőjátékokhoz](https://archiv.cserkesz.hu/sites/default/files/sites/default/files/imce/kalmar_jatek_szabalyzat_v03.pdf) készült online platform, amivel az állomások egyes árfolyamait, és a játékosok számláit online, központilag lehet kezelni.

## Implementáció

Jelenleg az eszközök ($S$) egy egyszerű Brown-mozgást végeznek egy drift-el együtt:
$$
  \mathrm{d}S = \alpha \mathrm{d}t + \sigma \mathrm{d}W
$$

A kliensek, vagyis az állomások egy egyedi random tényezővel térnek el az eszközök $S$ árától. 
