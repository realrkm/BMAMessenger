package com.example.bmamessenger

import com.google.gson.annotations.SerializedName

/**
 * Represents a single SMS message to be sent.
 *
 * @param id The unique identifier of the message.
 * @param fullname The full name of the recipient.
 * @param phone The phone number of the recipient.
 * @param message The content of the message.
 * @param flag A boolean flag with an unspecified purpose.
 * @param jobcardrefid The reference ID of the job card associated with this message.
 * @param document The document type/value associated with this message.
 */
data class SmsMessage(
    val id: Int,
    val fullname: String,
    val phone: String,
    val message: String,
    val flag: Boolean,
    val jobcardrefid: Int,
    @SerializedName(
        value = "document",
        alternate = ["Document", "document_type", "docType", "doctype"]
    )
    val document: String? = null
)
