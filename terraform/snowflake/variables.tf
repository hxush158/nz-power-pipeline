variable "snowflake_organization_name" {
  description = "Snowflake 组织名（账号标识 <组织名>-<账号名> 的前半部分）。"
  type        = string
}

variable "snowflake_account_name" {
  description = "Snowflake 账号名（账号标识的后半部分）。"
  type        = string
}

variable "snowflake_user" {
  description = "Terraform 使用的 Snowflake 用户（用密钥对登录，不用密码）。"
  type        = string
}

variable "snowflake_private_key_path" {
  description = "私钥文件路径，放在仓库外面。"
  type        = string
  default     = "~/.snowflake/rsa_key.p8"
}

variable "snowflake_role" {
  description = "Terraform 连接时使用的角色。学习环境先用 ACCOUNTADMIN，之后再收紧到 SYSADMIN / SECURITYADMIN 分开管。"
  type        = string
  default     = "ACCOUNTADMIN"
}
