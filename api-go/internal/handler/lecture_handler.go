// api-go/internal/handler/lecture_handler.go

package handler

import (
	"net/http"

	"github.com/gin-gonic/gin"
	"github.com/takumi-1234/OpenRAG/api-go/internal/middleware"
	"github.com/takumi-1234/OpenRAG/api-go/internal/model"
	"github.com/takumi-1234/OpenRAG/api-go/internal/service"
)

type LectureHandler struct {
	service *service.LectureService
}

func NewLectureHandler(service *service.LectureService) *LectureHandler {
	return &LectureHandler{service: service}
}

func (h *LectureHandler) CreateLecture(c *gin.Context) {
	var req model.CreateLectureRequest
	if err := c.ShouldBindJSON(&req); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
		return
	}

	// ★★★ middlewareパッケージを直接使用します ★★★
	userID := c.MustGet(middleware.AuthorizationPayloadKey).(int64)

	lecture, err := h.service.CreateLecture(c.Request.Context(), &req, userID)
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
		return
	}

	c.JSON(http.StatusCreated, lecture)
}

func (h *LectureHandler) GetLecturesByUserID(c *gin.Context) {
	// ★★★ middlewareパッケージを直接使用します ★★★
	userID := c.MustGet(middleware.AuthorizationPayloadKey).(int64)

	lectures, err := h.service.GetLecturesByUserID(c.Request.Context(), userID)
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
		return
	}

	c.JSON(http.StatusOK, lectures)
}
