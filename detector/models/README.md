# Modelos

Carpeta destino para los pesos YOLO11n en formato NCNN:

- `yolo11n_416.ncnn.param` (~50 KB, texto)
- `yolo11n_416.ncnn.bin` (~3 MB, binario)

Estos archivos **no están en el repo por default**. Se generan una vez con:

```bash
# En una laptop con Python 3.10+ (no en la Pi):
pip install ultralytics
python scripts/export_yolo_ncnn.py
```

El script descarga los pesos pre-entrenados de YOLO11n (COCO) desde Ultralytics y los exporta a NCNN con input 416×416. Una vez generados, se pueden commitear al repo o copiar manualmente a la Pi.

El detector los carga sólo cuando `YOLO_ENABLED=true` y el paquete `ncnn` está instalado. Si faltan, se loggea un warning y el detector sigue funcionando con el canal Hand-Ear de MediaPipe.
