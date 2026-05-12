# Laravel 11 + Filament 3 Setup Reference

## Minimum Requirements
- PHP 8.2+
- Composer 2.x
- PostgreSQL 14+ OR MySQL 8+

## Key Packages
- `filament/filament: ^3.2` — admin panel
- `laravel/sanctum` — API auth (if needed)
- `spatie/laravel-permission` — RBAC (optional)

## Filament Panel Config
```php
// bootstrap/app.php
use Filament\Panel;
use Filament\PanelProvider;

app()->bind(PanelProvider::class, function () {
    return new class extends PanelProvider {
        public function panel(Panel $panel): Panel
        {
            return $panel
                ->id('admin')
                ->path('admin')
                ->resources([
                    BookingResource::class,
                    PackageResource::class,
                ])
                ->widgets([]);
        }
    };
});
```

## Multi-Role Auth with Breeze + Filament
```php
// app/Models/User.php
class User extends Authenticatable
{
    public function role(): BelongsTo
    {
        return $this->belongsTo(Role::class);
    }

    public function isAdmin(): bool
    {
        return $this->role?->name === 'admin';
    }
}
```
