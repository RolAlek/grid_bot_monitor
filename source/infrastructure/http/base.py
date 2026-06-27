from collections.abc import Sequence
from http import HTTPMethod
from typing import Any, cast

from httpx import AsyncClient, Auth
from pydantic import BaseModel, TypeAdapter, ValidationError

from source.infrastructure.exceptions import HttpSerializationError, HttpValidationError
from source.infrastructure.http.types import HeaderTypes, IncExType, PayloadType, RequestJson, TError, TResponse


class BaseHTTPClient:
    def __init__(self, base_url: str, timeout: float | None = None, auth: Auth | None = None) -> None:
        self._base_url = base_url
        self._timeout = timeout
        self._auth = auth or Auth()

    async def get(
        self,
        path: str,
        response_model: type[TResponse],
        error_model: type[TError],
        *,
        headers: HeaderTypes | None = None,
        params: dict[str, Any] | None = None,
    ) -> TResponse | TError:
        return await self._execute(
            method=HTTPMethod.GET,
            path=path,
            response_model=response_model,
            error_model=error_model,
            headers=headers,
            params=params,
        )  # type: ignore[call-arg]

    async def post(
        self,
        path: str,
        response_model: type[TResponse],
        error_model: type[TError],
        *,
        params: dict[str, Any] | None = None,
        payload: PayloadType,
        request_model: type[BaseModel],
        headers: HeaderTypes | None = None,
        include: IncExType | None = None,
        exclude: IncExType | None = None,
        by_alias: bool = False,
        exclude_unset: bool = False,
        exclude_defaults: bool = False,
        exclude_none: bool = False,
    ) -> TResponse | TError:
        return await self._execute(  # type: ignore[call-arg]
            method=HTTPMethod.POST,
            path=path,
            response_model=response_model,
            error_model=error_model,
            params=params,
            payload=payload,
            request_model=request_model,
            headers=headers,
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
        response_model: type[TResponse],
        error_model: type[TError],
        *,
        params: dict[str, Any] | None = None,
        payload: PayloadType | None = None,
        request_model: type[BaseModel] | None = None,
        headers: HeaderTypes | None = None,
        include: IncExType | None = None,
        exclude: IncExType | None = None,
        by_alias: bool = False,
        exclude_unset: bool = False,
        exclude_defaults: bool = False,
        exclude_none: bool = False,
    ) -> TResponse | TError:
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

        async with AsyncClient(base_url=self._base_url, timeout=self._timeout, auth=self._auth) as client:
            response = await client.request(
                method=method,
                url=path,
                params=params,
                headers=headers,
                json=serialized_payload,
            )

        response.raise_for_status()

        return self._validate_response(
            content=await response.aread(),
            response_model=response_model,
            error_model=error_model,
        )

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

    def _validate_response[TResponse, TError](
        self,
        content: bytes,
        response_model: type[TResponse],
        error_model: type[TError],
    ) -> TResponse | TError:
        try:
            return TypeAdapter(response_model).validate_json(content)
        except ValidationError:
            return self._validate_error_response(
                content=content,
                error_model=error_model,
            )

    def _validate_error_response[TError](
        self,
        content: bytes,
        error_model: type[TError],
    ) -> TError:
        try:
            return TypeAdapter(error_model).validate_json(content)
        except ValidationError as validation_error:
            raise HttpValidationError(
                f"Failed to validate error response with model {error_model.__name__}",
                model_name=error_model.__name__,
                validation_errors=[dict(error) for error in validation_error.errors()],
                original_error=validation_error,
            ) from validation_error
