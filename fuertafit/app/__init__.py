"""Mi rutina Fuerta: generador y planificador de rutinas sobre el catálogo de FuertaFit.

Estructura MVC:
- models/       datos: SQLite (historial, calendario, estados de día, ajustes) y catálogo
- services/     lógica de negocio: generador, planificador, calendario, entrenador con IA (latente)
- controllers/  rutas /api: reciben la petición, llaman al modelo y devuelven la vista
- views/        presentación: serializadores JSON y la web estática (HTML, CSS, JS)
"""
