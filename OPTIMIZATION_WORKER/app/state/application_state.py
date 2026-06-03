from app.models.filter_type import FilterType
import asyncio


class ApplicationState:

    genetic_model = None

    model_ready = False

    startup_summary = None

    filter_locks = {
        FilterType.PASA_BAJA: asyncio.Lock(),
        FilterType.PASA_ALTA: asyncio.Lock(),
        FilterType.PASA_BANDA: asyncio.Lock(),
        FilterType.BANDA_RECHAZO: asyncio.Lock(),
    }
    