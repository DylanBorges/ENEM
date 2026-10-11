from typing import Any
import numpy as np

from tri_core.calibration import MMLEMCalibration, CalibrationOptions
from tri_core.models import ItemParameter


def run_async_calibration_task(
    response_matrix_list: list[list[int]],
    options_dict: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Tarefa assíncrona Celery para calibração offline de microdados."""
    responses = np.array(response_matrix_list, dtype=np.int32)
    opts = CalibrationOptions(**(options_dict or {}))

    calibrator = MMLEMCalibration()
    res = calibrator.calibrate(responses, options=opts)

    return {
        "converged": res.converged,
        "iterations": res.iterations,
        "log_marginal_likelihood": res.log_marginal_likelihood,
        "items": [
            {"a": itm.a, "b": itm.b, "c": itm.c, "D": itm.D, "item_id": itm.item_id}
            for itm in res.items
        ],
    }
