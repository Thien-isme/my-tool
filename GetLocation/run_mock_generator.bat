@echo off
echo ==========================================
echo         MOCK ADDRESS GENERATOR
echo ==========================================
echo.
echo Kiem tra va cai dat thu vien can thiet...
pip install -r requirements.txt
if %errorlevel% neq 0 (
    echo [!] Canh bao: Co loi khi cai dat thu vien. Co the ban chua cai Python hoac pip.
)

echo.
set /p city="Nhap Tinh hoac Thanh pho (VD: Ho Chi Minh, Ha Noi, Da Nang): "
set /p count="Nhap so luong dia chi can tao (mac dinh: 100): "

if "%count%"=="" set count=100

echo.
echo Dang tao %count% dia chi cho "%city%"...
python generate_mock_address.py --city "%city%" --count %count%

echo.
pause
