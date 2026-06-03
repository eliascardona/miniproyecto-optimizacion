from app.state.application_state import (
    ApplicationState
)


class LockService:

    @staticmethod
    def get_lock(filter_type):

        return (
            ApplicationState
            .filter_locks[filter_type]
        )
    
