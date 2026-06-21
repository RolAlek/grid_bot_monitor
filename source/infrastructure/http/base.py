from collections.abc import Mapping, Sequence
from http import HTTPMethod
from typing import Any, TypeVar, cast

from httpx import AsyncClient, Auth
from pydantic import BaseModel, TypeAdapter

from source.infrastructure.exceptions import HttpSerializationError


PrimitiveData = str | int | float | bool | None

TResponse = TypeVar("TResponse", bound=BaseModel)

IncExType = set[int] | set[str] | dict[int, Any] | dict[str, Any]
PayloadType = BaseModel | Sequence[BaseModel]
ParamType = (
    Mapping[str, PrimitiveData | Sequence[PrimitiveData]]
    | list[tuple[str, PrimitiveData]]
    | tuple[tuple[str, PrimitiveData], ...]
    | str
    | bytes
)
RequestJson = Mapping[str, Any] | str | bytes


class BaseHTTPClient:
    def __init__(self, base_url: str, timeout: float | None = None, auth: Auth | None = None) -> None:
        self._base_url = base_url
        self._timeout = timeout
        self._auth = auth or Auth()

        self._client = AsyncClient(base_url=self._base_url, timeout=self._timeout, auth=self._auth)

    async def get(
        self,
        path: str,
        response_model: type[BaseModel],
        *,
        params: dict[str, Any] | None = None,
    ) -> TResponse:
        return await self._execute(method=HTTPMethod.GET, path=path, response_model=response_model, params=params)  # type: ignore[call-arg]

    async def post(
        self,
        path: str,
        *,
        payload: PayloadType,
        response_model: type[BaseModel],
        request_model: type[BaseModel],
        include: IncExType | None = None,
        exclude: IncExType | None = None,
        by_alias: bool = False,
        exclude_unset: bool = False,
        exclude_defaults: bool = False,
        exclude_none: bool = False,
    ) -> TResponse:
        return await self.post(  # type: ignore[call-arg]
            method=HTTPMethod.POST,
            path=path,
            payload=payload,
            request_model=request_model,
            response_model=response_model,
            include=include,
            exclude=exclude,
            by_alias=by_alias,
            exclude_unset=exclude_unset,
            exclude_defaults=exclude_defaults,
            exclude_none=exclude_none,
        )

    async def _execute(
        self,
        method: HTTPMethod,
        path: str,
        response_model: type[BaseModel],
        *,
        params: dict[str, Any] | None = None,
        payload: PayloadType | None = None,
        request_model: type[BaseModel] | None = None,
        include: IncExType | None,
        exclude: IncExType | None,
        by_alias: bool = False,
        exclude_unset: bool = False,
        exclude_defaults: bool = False,
        exclude_none: bool = False,
    ) -> TResponse:
        serialized_payload: RequestJson | None = None

        if payload and request_model:
            serialized_payload = self._serialize_payload(
                payload=payload,
                request_model=request_model,
                include=include,
                exclude=exclude,
                by_alias=by_alias,
                exclude_unset=exclude_unset,
                exclude_defaults=exclude_defaults,
                exclude_none=exclude_none,
            )

        async with self._client as client:
            response = await client.request(
                method=method,
                url=path,
                params=params,
                json=serialized_payload,
            )

        response.raise_for_status()

        parsed_response = TypeAdapter(response_model).validate_json(await response.aread())

        return cast("TResponse", parsed_response)

    @staticmethod
    def _serialize_payload(
        payload: BaseModel | Sequence[BaseModel],
        request_model: type[BaseModel],
        include: IncExType | None,
        exclude: IncExType | None,
        by_alias: bool,
        exclude_unset: bool,
        exclude_defaults: bool,
        exclude_none: bool,
    ) -> RequestJson:

        try:
            if isinstance(payload, Sequence) and not isinstance(payload, str):
                serialized = TypeAdapter(list[request_model]).dump_python(  # type: ignore[valid-type]
                    list(payload),
                    mode="json",
                    include=include,
                    exclude=exclude,
                    by_alias=by_alias,
                    exclude_unset=exclude_unset,
                    exclude_defaults=exclude_defaults,
                    exclude_none=exclude_none,
                )
            else:
                serialized = TypeAdapter(request_model).dump_python(
                    payload,
                    mode="json",
                    include=include,
                    exclude=exclude,
                    by_alias=by_alias,
                    exclude_unset=exclude_unset,
                    exclude_defaults=exclude_defaults,
                    exclude_none=exclude_none,
                )

            return cast("RequestJson", serialized)
        except Exception as error:
            raise HttpSerializationError(
                f"Failed to serialize request payload with model {request_model.__name__}",
                model_name=request_model.__name__,
                original_error=error,
            ) from error
