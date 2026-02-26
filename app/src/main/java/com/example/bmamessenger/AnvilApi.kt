package com.example.bmamessenger

import okhttp3.ResponseBody
import retrofit2.Response
import retrofit2.http.Field
import retrofit2.http.FormUrlEncoded
import retrofit2.http.GET
import retrofit2.http.POST
import retrofit2.http.Path
import retrofit2.http.Query
import retrofit2.http.Streaming

data class LoginUser(
    val email: String,
    val roleId: String
)

data class LoginResponse(
    val success: Boolean,
    val user: LoginUser? = null,
    val error: String? = null
)

/**
 * Defines the API endpoints for interacting with the Anvil service.
 * This interface is used by Retrofit to make network requests.
 */
interface AnvilApi {
    @FormUrlEncoded
    @POST("_/api/verify-login")
    suspend fun login(
        @Field("email") email: String,
        @Field("password") password: String
    ): Response<LoginResponse>

    /**
     * Retrieves a list of pending SMS messages from the Anvil API.
     *
     * @return A list of [SmsMessage] objects representing the pending SMS messages.
     */
    @GET("_/api/pending-sms")
    suspend fun getPendingSms(): List<SmsMessage>

    /**
     * Marks a specific SMS message as sent in the Anvil API.
     *
     * @param id The unique identifier of the SMS message to mark as sent.
     */
    @POST("_/api/mark-sent/{id}")
    suspend fun markAsSent(@Path("id") id: Int)

    /**
     * Generates a PDF document for a given job card ID.
     *
     * @param jobCardId The unique identifier of the job card.
     * @param document The selected document label/type (Invoice, Confirm, Quote, etc).
     * @return A [ResponseBody] containing the PDF file.
     */
    @Streaming
    @GET("_/api/generate-pdf/{jobcardid}")
    suspend fun generatePdf(
        @Path("jobcardid") jobCardId: Int,
        @Query("document") document: String
    ): ResponseBody
}
