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

variable "azure_tenant_id" {
  description = "Azure 租户 ID（az account show --query tenantId -o tsv）。Storage Integration 用它指向存储账号所在的租户；不是密钥，但按约定走环境变量。"
  type        = string
}

variable "snowflake_private_key_passphrase" {
  description = "Terraform 用户私钥的密码短语（私钥已加密时必填，未加密时留空）。通过环境变量 TF_VAR_snowflake_private_key_passphrase 传入，不写进文件。"
  type        = string
  sensitive   = true
  default     = null
}

variable "chemq_reporter_user_name" {
  description = "给 ChemQ 引擎用的只读服务用户名。"
  type        = string
  default     = "CHEMQ_REPORTER"
}

variable "chemq_reporter_public_key_path" {
  description = "ChemQ 只读用户的公钥文件路径（私钥由 ChemQ 保管，不经过本仓库）。"
  type        = string
  default     = "~/.snowflake/chemq_reporter.pub"
}

variable "dbt_user_name" {
  description = "dbt 用的服务用户名（以 NZ_TRANSFORMER 身份在 STAGING/MART 建表建视图）。"
  type        = string
  default     = "DBT_SVC"
}

variable "dbt_public_key_path" {
  description = "dbt 用户的公钥文件路径（私钥只留在本机，不进仓库）。"
  type        = string
  default     = "~/.snowflake/dbt_svc.pub"
}
