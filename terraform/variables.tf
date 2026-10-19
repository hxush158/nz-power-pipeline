variable "subscription_id" {
  description = "Azure 订阅 ID。通过环境变量 TF_VAR_subscription_id 传入，不写进仓库。"
  type        = string
}

variable "alert_email" {
  description = "预算告警收件邮箱。通过环境变量 TF_VAR_alert_email 传入，不写进仓库。"
  type        = string
  sensitive   = true
}

variable "location" {
  description = "Azure 区域。"
  type        = string
  default     = "australiaeast"
}

variable "budget_amount" {
  description = "每月预算金额（按账单币种）。"
  type        = number
  default     = 10
}
