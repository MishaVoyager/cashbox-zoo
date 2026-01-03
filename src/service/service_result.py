from dataclasses import dataclass
from typing import Generic, TypeVar, Optional, Callable

T = TypeVar('T')
U = TypeVar('U')


@dataclass(frozen=True)
class ServiceResult(Generic[T]):
    data: Optional[T] = None
    error: Optional[str] = None
    error_code: Optional[int] = None

    @classmethod
    def success(cls, data: T) -> 'ServiceResult[T]':
        return cls(data=data)

    @classmethod
    def failure(cls, error: str, error_code: Optional[int] = None) -> 'ServiceResult[T]':
        return cls(error=error, error_code=error_code)

    @property
    def is_success(self) -> bool:
        return self.error is None

    @property
    def is_failure(self) -> bool:
        return not self.is_success

    def unwrap(self) -> T:
        if self.is_success:
            return self.data
        raise ValueError(f"[{self.error_code}] {self.error}" if self.error_code else self.error)

    def map(self, func: Callable[[T], U]) -> 'ServiceResult[U]':
        return ServiceResult.success(func(self.data)) if self.is_success else self
