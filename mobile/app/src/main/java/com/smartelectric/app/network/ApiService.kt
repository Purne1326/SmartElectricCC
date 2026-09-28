package com.smartelectric.app.network

import com.smartelectric.app.model.*
import retrofit2.Retrofit
import retrofit2.converter.gson.GsonConverterFactory
import retrofit2.http.Body
import retrofit2.http.GET
import retrofit2.http.POST
import retrofit2.http.Query

interface ApiService {

    @GET("api/status")
    suspend fun getSystemStatus(): SystemStatus

    @GET("api/metrics")
    suspend fun getMetrics(
        @Query("range_type") rangeType: String
    ): MetricsResponse

    @GET("api/history")
    suspend fun getHistory(
        @Query("limit") limit: Int
    ): List<HistoryRecord>

    @GET("api/logs")
    suspend fun getLogs(
        @Query("limit") limit: Int
    ): List<LogRecord>

    @POST("api/control")
    suspend fun controlRelay(
        @Body request: RelayControlRequest
    ): ControlResponse
}

object RetrofitClient {
    private var lastIp: String? = null
    private var apiServiceInstance: ApiService? = null

    /**
     * Rebuilds the Retrofit instance if the Gateway IP has been modified in settings,
     * ensuring seamless dynamic switching between local IPs or remote cloud IPs.
     */
    fun getService(gatewayIp: String): ApiService {
        // Strip out protocol prefixes if user accidentally types them in
        val formattedIp = gatewayIp
            .replace("http://", "")
            .replace("https://", "")
            .trim()

        if (apiServiceInstance == null || lastIp != formattedIp) {
            lastIp = formattedIp
            
            val baseUrl = if (formattedIp.contains(":")) {
                "http://$formattedIp/"
            } else {
                "http://$formattedIp:8000/"
            }

            val retrofit = Retrofit.Builder()
                .baseUrl(baseUrl)
                .addConverterFactory(GsonConverterFactory.create())
                .build()
                
            apiServiceInstance = retrofit.create(ApiService::class.java)
        }
        return apiServiceInstance!!
    }
}
