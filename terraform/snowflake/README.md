# Snowflake 资源（Terraform）

目前只有骨架：provider 版本、认证变量和远程状态，还没有任何资源。
账号本身（注册、第一个管理员、MFA、给 Terraform 用户登记公钥）需要手工完成，之后才能 `terraform init`。

计划由 Terraform 管理（周一对照官方文档确认资源名后再写）：
Warehouse（X-Small，AUTO_SUSPEND = 60）、Resource Monitor、数据库 NZ_POWER、schema RAW / STAGING / MART、
角色 NZ_LOADER / NZ_TRANSFORMER / NZ_REPORTER 及授权、Storage Integration。

## 变量
通过环境变量传入，不写进文件、不提交：

    export TF_VAR_snowflake_organization_name=...
    export TF_VAR_snowflake_account_name=...
    export TF_VAR_snowflake_user=...

私钥默认读 `~/.snowflake/rsa_key.p8`（仓库外，权限 600）。

## 运行
    cd terraform/snowflake
    terraform init
    terraform plan

`.terraform.lock.hcl` 要提交；`.terraform/`、`*.tfstate*`、`*.tfvars`、`*.p8` 已在 .gitignore。

## Storage Integration
`storage_integration.tf` 建 `INT_AZURE_RAW`，只放开 `raw/prices/`。apply 之后：

1. 在 Snowflake 里运行 `DESC STORAGE INTEGRATION INT_AZURE_RAW;`，取出 `AZURE_CONSENT_URL` 和 `AZURE_MULTI_TENANT_APP_NAME`。
2. 用 Azure 租户管理员账号打开 consent URL，点同意。
3. 在 Azure 存储账号 `nzpowerhxu` 上，给上面那个应用（名字取 `AZURE_MULTI_TENANT_APP_NAME` 里下划线之前的部分）授予 `Storage Blob Data Reader`。授权生效可能要等几分钟。

变量：`export TF_VAR_azure_tenant_id="$(az account show --query tenantId -o tsv)"`
