# Corporation v22.4 — Selected News Images

В обновлении используются именно изображения из присланного коллажа пользователя.

Что сделано:
- коллаж разделён на 7 отдельных изображений: McDonald's, NVIDIA, Spotify, KFC, BMW, Tesla, Toyota;
- изображения сохранены локально в `web/news/*.webp`;
- все 7 компаний в `MARKET_NEWS_TEMPLATES` используют эти локальные картинки;
- уже опубликованные новости тоже начинают показывать новые изображения;
- для мобильной версии добавлен `object-fit: contain` и квадратная область, поэтому логотипы, текст и ключевые объекты не обрезаются;
- изображения оптимизированы в WebP 900×900, чтобы не перегружать Telegram Mini App.

## Установка

Распакуй ZIP в корень проекта Corporation и выполни:

```powershell
python .\apply_update_v22_4_selected_news_images.py
```

После успешного применения:

```powershell
git status
git add app.py web/style.css web/index.html web/news
git commit -m "Use selected company news images"
git push origin main
```

Папку `backup_before_v22_4_news_images_...` в Git не добавляй.
