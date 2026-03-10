package com.tonbil.aifirewall.data.repository

import com.tonbil.aifirewall.data.remote.ApiRoutes
import com.tonbil.aifirewall.data.remote.dto.*
import io.ktor.client.HttpClient
import io.ktor.client.call.body
import io.ktor.client.request.delete
import io.ktor.client.request.get
import io.ktor.client.request.patch
import io.ktor.client.request.post
import io.ktor.client.request.setBody
import io.ktor.http.ContentType
import io.ktor.http.contentType

class ContentCategoryRepository(private val client: HttpClient) {

    suspend fun getCategories(): Result<List<ContentCategoryDto>> = runCatching {
        client.get(ApiRoutes.CONTENT_CATEGORIES).body()
    }

    suspend fun createCategory(dto: ContentCategoryCreateDto): Result<ContentCategoryDto> = runCatching {
        client.post(ApiRoutes.CONTENT_CATEGORIES) {
            contentType(ContentType.Application.Json)
            setBody(dto)
        }.body()
    }

    suspend fun updateCategory(id: Int, dto: ContentCategoryUpdateDto): Result<ContentCategoryDto> = runCatching {
        client.patch(ApiRoutes.contentCategoryDetail(id)) {
            contentType(ContentType.Application.Json)
            setBody(dto)
        }.body()
    }

    suspend fun deleteCategory(id: Int): Result<Unit> = runCatching {
        client.delete(ApiRoutes.contentCategoryDetail(id))
    }
}
