import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { Button } from './components/ui/button';
import { Input } from './components/ui/input';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from './components/ui/card';
import { Progress } from './components/ui/progress';
import { Badge } from './components/ui/badge';
import { Separator } from './components/ui/separator';
import { Alert, AlertDescription } from './components/ui/alert';
import { Skeleton } from './components/ui/skeleton';
import { 
  Play, 
  Eye, 
  Heart, 
  User, 
  Clock,
  Share2,
  ExternalLink,
  MessageCircle,
  Instagram,
  Sparkles,
  CheckCircle,
  AlertCircle,
  Zap,
  Key
} from 'lucide-react';

// API URL из переменной окружения или fallback на localhost:8000
const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

export default function App() {
  const [url, setUrl] = useState('');
  const [sessionId, setSessionId] = useState('');
  const [csrfToken, setCsrfToken] = useState('');
  const [dsUserId, setDsUserId] = useState('');
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [progress, setProgress] = useState(0);

  // Загружаем сохраненные cookies при старте приложения
  useEffect(() => {
    const savedSessionId = sessionStorage.getItem('instagram_sessionid');
    const savedCsrfToken = sessionStorage.getItem('instagram_csrftoken');
    const savedDsUserId = sessionStorage.getItem('instagram_ds_user_id');
    
    if (savedSessionId) setSessionId(savedSessionId);
    if (savedCsrfToken) setCsrfToken(savedCsrfToken);
    if (savedDsUserId) setDsUserId(savedDsUserId);
  }, []);

  // Сохраняем cookies при их изменении
  const updateSessionId = (value) => {
    setSessionId(value);
    if (value.trim()) {
      sessionStorage.setItem('instagram_sessionid', value);
    } else {
      sessionStorage.removeItem('instagram_sessionid');
    }
  };

  const updateCsrfToken = (value) => {
    setCsrfToken(value);
    if (value.trim()) {
      sessionStorage.setItem('instagram_csrftoken', value);
    } else {
      sessionStorage.removeItem('instagram_csrftoken');
    }
  };

  const updateDsUserId = (value) => {
    setDsUserId(value);
    if (value.trim()) {
      sessionStorage.setItem('instagram_ds_user_id', value);
    } else {
      sessionStorage.removeItem('instagram_ds_user_id');
    }
  };

  // Функция для очистки всех сохраненных cookies
  const clearSavedCookies = () => {
    sessionStorage.removeItem('instagram_sessionid');
    sessionStorage.removeItem('instagram_csrftoken');
    sessionStorage.removeItem('instagram_ds_user_id');
    setSessionId('');
    setCsrfToken('');
    setDsUserId('');
  };

  // Функция для детекции Instagram URL
  const isInstagramUrl = (url) => {
    return url.toLowerCase().includes('instagram.com');
  };

  // Функция для детекции VK Video URL
  const isVkUrl = (url) => {
    const urlLower = url.toLowerCase();
    return urlLower.includes('vk.com/video') || 
           urlLower.includes('vk.com/clip') || 
           urlLower.includes('vk.ru/video') || 
           urlLower.includes('vk.ru/clip') ||
           urlLower.includes('m.vk.com/video') ||
           urlLower.includes('m.vk.ru/video');
  };

  // Функция для детекции Likee URL
  const isLikeeUrl = (url) => {
    const urlLower = url.toLowerCase();
    return urlLower.includes('likee.video') || 
           urlLower.includes('likee.com') || 
           urlLower.includes('l.likee.video');
  };

  // Функция для проверки валидности Instagram cookies
  const hasValidInstagramCookies = () => {
    return sessionId.trim() && csrfToken.trim() && dsUserId.trim();
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    
    // Валидация cookies для Instagram
    if (isInstagramUrl(url) && !hasValidInstagramCookies()) {
      setError('Для Instagram ссылок необходимо указать cookies (sessionid, csrftoken, ds_user_id)');
      return;
    }
    
    setLoading(true);
    setError('');
    setData(null);
    setProgress(10);
    try {
      const formData = new URLSearchParams({ url });
      if (isInstagramUrl(url) && hasValidInstagramCookies()) {
        formData.append('sessionid', sessionId);
        formData.append('csrftoken', csrfToken);
        formData.append('ds_user_id', dsUserId);
      }
      const res = await axios.post(`${API_URL}/parse`, formData);
      setProgress(60);
      setData(res.data);
      setProgress(100);
    } catch (err) {
      setError(err.response?.data?.detail || 'Ошибка запроса');
      setProgress(0);
    } finally {
      setLoading(false);
    }
  };



  const getPlatformBadge = (url) => {
    if (url?.includes('tiktok')) return { name: 'TikTok', variant: 'default' };
    if (url?.includes('instagram')) return { name: 'Instagram', variant: 'secondary' };
    if (url?.includes('youtube')) return { name: 'YouTube', variant: 'destructive' };
    return { name: 'Неизвестно', variant: 'outline' };
  };

  const formatNumber = (num) => {
    if (!num) return 'N/A';
    return num.toLocaleString();
  };

  // Функция для очистки и валидации thumbnail URL
  const cleanThumbnailUrl = (url) => {
    if (!url) return null;
    
    // Убираем символ @ в начале URL
    let cleanedUrl = url.trim().replace(/^@+/, '');
    
    // Убираем другие некорректные символы в начале
    while (cleanedUrl && !cleanedUrl.startsWith('http')) {
      cleanedUrl = cleanedUrl.substring(1);
    }
    
    // Проверяем что URL валидный
    try {
      new URL(cleanedUrl);
      return cleanedUrl;
    } catch (e) {
      console.warn('Невалидный thumbnail URL:', url, '-> очищенный:', cleanedUrl);
      return null;
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 via-blue-50 to-indigo-100 dark:from-slate-950 dark:via-slate-900 dark:to-slate-800">
      {/* Header */}
      <header className="border-b bg-background/80 backdrop-blur-sm sticky top-0 z-50">
        <div className="container max-w-6xl mx-auto px-4 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="p-2 bg-primary/10 rounded-lg">
                <Sparkles className="w-6 h-6 text-primary" />
              </div>
              <div>
                <h1 className="text-xl font-bold text-foreground">MetaParser</h1>
                <p className="text-sm text-muted-foreground">Парсер социальных сетей</p>
              </div>
            </div>
            <Badge variant="success" className="flex items-center gap-1">
              <Zap className="w-3 h-3" />
              Pro версия
            </Badge>
          </div>
        </div>
      </header>

      <div className="container max-w-6xl mx-auto px-4 py-8 space-y-8">
        {/* Hero Section */}
        <div className="text-center space-y-4">
          <div className="inline-flex items-center gap-2 px-3 py-1 bg-primary/10 text-primary rounded-full text-sm font-medium">
            <CheckCircle className="w-4 h-4" />
            Поддержка TikTok, Instagram, YouTube
          </div>
          <h2 className="text-4xl md:text-6xl font-bold bg-gradient-to-r from-slate-900 via-blue-600 to-indigo-600 bg-clip-text text-transparent dark:from-slate-100 dark:via-blue-400 dark:to-indigo-400">
            Получите метаданные любого контента
          </h2>
          <p className="text-lg text-muted-foreground max-w-2xl mx-auto">
            Быстро извлекайте информацию о видео, постах и их авторах из популярных социальных платформ
          </p>
        </div>

        {/* Input Form */}
        <Card className="border-2 border-dashed border-muted hover:border-primary/50 transition-all duration-300">
          <CardHeader className="text-center">
            <CardTitle className="flex items-center justify-center gap-2 text-2xl">
              <ExternalLink className="w-6 h-6 text-primary" />
              Вставьте ссылку
            </CardTitle>
            <CardDescription className="text-base">
              Введите URL видео или поста для получения детальной информации. Поддерживаются TikTok, Instagram, YouTube, VK Video и Likee
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <form onSubmit={handleSubmit} className="space-y-4">
              <div className="flex flex-col sm:flex-row gap-3">
                <div className="flex-1 relative">
                  <Input
                    type="url"
                    placeholder="https://vk.com/video..., https://likee.video/@username..., https://tiktok.com/..."
                    value={url}
                    onChange={e => setUrl(e.target.value)}
                    required
                    className="pr-12 h-12 text-base"
                  />
                  <div className="absolute right-3 top-1/2 -translate-y-1/2">
                    <ExternalLink className="w-4 h-4 text-muted-foreground" />
                  </div>
                </div>
                <Button 
                  type="submit" 
                  disabled={loading} 
                  size="lg"
                  className="h-12 px-8 min-w-[140px]"
                >
                  {loading ? (
                    <>
                      <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-current mr-2"></div>
                      Обработка...
                    </>
                  ) : (
                    <>
                      <Play className="w-4 h-4 mr-2" />
                      Анализировать
                    </>
                  )}
                </Button>
              </div>
              
              {/* Условное поле cookies для Instagram */}
              {isInstagramUrl(url) && (
                <div className="space-y-4 p-4 bg-gradient-to-r from-purple-50 to-pink-50 border border-purple-200 rounded-lg dark:from-purple-950 dark:to-pink-950 dark:border-purple-800">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <Key className="w-4 h-4 text-purple-600 dark:text-purple-400" />
                      <label className="text-sm font-medium text-purple-900 dark:text-purple-100">
                        Instagram Cookies *
                      </label>
                      {hasValidInstagramCookies() && (
                        <span className="inline-flex items-center px-2 py-1 text-xs font-medium bg-green-100 text-green-800 rounded-full dark:bg-green-900 dark:text-green-200">
                          ✓ Сохранено
                        </span>
                      )}
                    </div>
                    {hasValidInstagramCookies() && (
                      <button
                        type="button"
                        onClick={clearSavedCookies}
                        className="text-xs text-purple-600 hover:text-purple-800 dark:text-purple-400 dark:hover:text-purple-200 underline"
                      >
                        Очистить cookies
                      </button>
                    )}
                  </div>
                  
                  <div className="grid grid-cols-1 gap-3">
                    {/* SessionID */}
                    <div className="space-y-1">
                      <label className="text-xs font-medium text-purple-800 dark:text-purple-200">
                        Session ID
                      </label>
                      <textarea
                        placeholder="Значение sessionid из браузера (например: 12345678%3AaBC123dEf...)"
                        value={sessionId}
                        onChange={e => updateSessionId(e.target.value)}
                        required={isInstagramUrl(url)}
                        rows={2}
                        className="w-full text-sm border-purple-300 focus:border-purple-500 dark:border-purple-700 rounded-md resize-none"
                      />
                    </div>
                    
                    {/* CSRF Token */}
                    <div className="space-y-1">
                      <label className="text-xs font-medium text-purple-800 dark:text-purple-200">
                        CSRF Token
                      </label>
                      <textarea
                        placeholder="Значение csrftoken из браузера (например: abc123DEF456ghi...)"
                        value={csrfToken}
                        onChange={e => updateCsrfToken(e.target.value)}
                        required={isInstagramUrl(url)}
                        rows={2}
                        className="w-full text-sm border-purple-300 focus:border-purple-500 dark:border-purple-700 rounded-md resize-none"
                      />
                    </div>
                    
                    {/* DS User ID */}
                    <div className="space-y-1">
                      <label className="text-xs font-medium text-purple-800 dark:text-purple-200">
                        DS User ID
                      </label>
                      <textarea
                        placeholder="Значение ds_user_id из браузера (например: 12345678)"
                        value={dsUserId}
                        onChange={e => updateDsUserId(e.target.value)}
                        required={isInstagramUrl(url)}
                        rows={1}
                        className="w-full text-sm border-purple-300 focus:border-purple-500 dark:border-purple-700 rounded-md resize-none"
                      />
                    </div>
                  </div>
                  
                  <p className="text-xs text-muted-foreground">
                    Скопируйте cookies из браузера для авторизации в Instagram. 
                    <br />
                    Данные автоматически сохраняются в текущей сессии браузера.
                    <br />
                    <strong>Как получить:</strong> F12 → Application/Storage → Cookies → instagram.com → скопируйте значения sessionid, csrftoken, ds_user_id
                  </p>
                </div>
              )}
            </form>

            {/* Supported Platforms */}
            <div className="flex flex-wrap items-center justify-center gap-2 pt-2">
              <span className="text-sm text-muted-foreground">Поддерживаются:</span>
              <Badge variant="outline">TikTok</Badge>
              <Badge variant="outline">Instagram</Badge>
              <Badge variant="outline">YouTube</Badge>
              <Badge variant="outline">VK Video</Badge>
              <Badge variant="outline">Likee</Badge>
            </div>
          </CardContent>
        </Card>

        {/* Progress */}
        {progress > 0 && progress < 100 && (
          <Card className="border-primary/20 bg-primary/5">
            <CardContent className="pt-6">
              <div className="space-y-3">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-primary"></div>
                    <span className="font-medium">Обработка запроса...</span>
                  </div>
                  <span className="text-sm font-medium">{progress}%</span>
                </div>
                <Progress value={progress} className="h-2" />
              </div>
            </CardContent>
          </Card>
        )}

        {/* Error Alert */}
        {error && (
          <Alert variant="destructive">
            <AlertCircle className="h-4 w-4" />
            <AlertDescription className="font-medium">
              {error}
            </AlertDescription>
          </Alert>
        )}

        {/* Loading Skeleton */}
        {loading && !data && (
          <Card>
            <CardContent className="p-0">
              <Skeleton className="h-64 w-full rounded-t-lg" />
              <div className="p-6 space-y-4">
                <Skeleton className="h-8 w-3/4" />
                <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                  <Skeleton className="h-6 w-full" />
                  <Skeleton className="h-6 w-full" />
                  <Skeleton className="h-6 w-full" />
                </div>
                <Skeleton className="h-20 w-full" />
                <Skeleton className="h-10 w-40" />
              </div>
            </CardContent>
          </Card>
        )}

        {/* Results */}
        {data && (
          <Card className="overflow-hidden shadow-xl border-0 bg-background/50 backdrop-blur-sm">
            <CardContent className="p-0">
              {/* Thumbnail */}
              {data.thumbnail && cleanThumbnailUrl(data.thumbnail) && (
                <div className="relative overflow-hidden">
                  <img 
                    src={cleanThumbnailUrl(data.thumbnail)} 
                    alt="preview" 
                    className="w-full h-80 object-cover transition-transform duration-300 hover:scale-105"
                    onError={(e) => {
                      console.error('Ошибка загрузки изображения:', data.thumbnail);
                      e.target.style.display = 'none';
                    }}
                  />
                  <div className="absolute inset-0 bg-gradient-to-t from-black/60 via-transparent to-transparent" />
                  <div className="absolute top-4 left-4">
                    <Badge variant={getPlatformBadge(data.url).variant} className="text-white bg-black/20 backdrop-blur-sm border-white/20">
                      {getPlatformBadge(data.url).name}
                    </Badge>
                  </div>
                  <div className="absolute bottom-4 right-4">
                    <Button variant="secondary" size="sm" className="bg-white/20 backdrop-blur-sm border-white/20 text-white hover:bg-white/30">
                      <Share2 className="w-4 h-4 mr-2" />
                      Поделиться
                    </Button>
                  </div>
                </div>
              )}

              <div className="p-8 space-y-6">
                {/* Title */}
                <div className="space-y-2">
                  <h2 className="text-3xl font-bold leading-tight">{data.title}</h2>
                  <div className="flex items-center gap-2 text-muted-foreground">
                    <Clock className="w-4 h-4" />
                    <span className="text-sm">Обработано только что</span>
                  </div>
                </div>

                <Separator />

                {/* Stats Grid */}
                <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
                  <Card className="p-4 bg-gradient-to-br from-blue-50 to-blue-100 border-blue-200 dark:from-blue-950 dark:to-blue-900 dark:border-blue-800">
                    <div className="flex items-center gap-3">
                      <div className="p-2 bg-blue-500/10 rounded-lg">
                        <User className="w-5 h-5 text-blue-600 dark:text-blue-400" />
                      </div>
                      <div>
                        <p className="text-sm font-medium text-blue-900 dark:text-blue-100">Автор</p>
                        <p className="text-lg font-bold text-blue-700 dark:text-blue-300">{data.author}</p>
                      </div>
                    </div>
                  </Card>

                  <Card className="p-4 bg-gradient-to-br from-green-50 to-green-100 border-green-200 dark:from-green-950 dark:to-green-900 dark:border-green-800">
                    <div className="flex items-center gap-3">
                      <div className="p-2 bg-green-500/10 rounded-lg">
                        <Eye className="w-5 h-5 text-green-600 dark:text-green-400" />
                      </div>
                      <div>
                        <p className="text-sm font-medium text-green-900 dark:text-green-100">Просмотры</p>
                        <p className="text-lg font-bold text-green-700 dark:text-green-300">{formatNumber(data.views)}</p>
                      </div>
                    </div>
                  </Card>

                  <Card className="p-4 bg-gradient-to-br from-red-50 to-red-100 border-red-200 dark:from-red-950 dark:to-red-900 dark:border-red-800">
                    <div className="flex items-center gap-3">
                      <div className="p-2 bg-red-500/10 rounded-lg">
                        <Heart className="w-5 h-5 text-red-600 dark:text-red-400" />
                      </div>
                      <div>
                        <p className="text-sm font-medium text-red-900 dark:text-red-100">Лайки</p>
                        <p className="text-lg font-bold text-red-700 dark:text-red-300">{formatNumber(data.likes)}</p>
                      </div>
                    </div>
                  </Card>

                  <Card className="p-4 bg-gradient-to-br from-orange-50 to-orange-100 border-orange-200 dark:from-orange-950 dark:to-orange-900 dark:border-orange-800">
                    <div className="flex items-center gap-3">
                      <div className="p-2 bg-orange-500/10 rounded-lg">
                        <MessageCircle className="w-5 h-5 text-orange-600 dark:text-orange-400" />
                      </div>
                      <div>
                        <p className="text-sm font-medium text-orange-900 dark:text-orange-100">Комментарии</p>
                        <p className="text-lg font-bold text-orange-700 dark:text-orange-300">{formatNumber(data.comment_count)}</p>
                      </div>
                    </div>
                  </Card>
                </div>

                {/* Description */}
                {data.description && (
                  <div className="space-y-3">
                    <h3 className="text-lg font-semibold flex items-center gap-2">
                      <div className="w-1 h-5 bg-primary rounded-full"></div>
                      Описание
                    </h3>
                    <Card className="p-4 bg-muted/50">
                      <p className="text-muted-foreground leading-relaxed">{data.description}</p>
                    </Card>
                  </div>
                )}


              </div>
            </CardContent>
          </Card>
        )}

        {/* Footer */}
        <div className="text-center pt-8 border-t">
          <p className="text-sm text-muted-foreground">
            Создано с ❤️ для удобного парсинга социальных сетей
          </p>
        </div>
      </div>
    </div>
  );
} 