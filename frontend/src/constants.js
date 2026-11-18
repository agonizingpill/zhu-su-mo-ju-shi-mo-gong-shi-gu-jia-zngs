export const ROLES={admin:'车间负责人',estimator:'工艺估价员',viewer:'只读观察员'};
export const STATES={draft:'待估算',calculating:'计算中',estimated:'已估工时',requested:'待机时承诺',committed:'已承诺锁定',failed:'计算失败'};
export const STEELS=['P20','H13','S136'];

export const EXECUTION_STATES={running:'试模进行中',completed:'已完工待结算',settled:'实绩已签结'};
export const REVIEW_STATES={draft:'待主管复核',signed:'主管已签结'};

export const MAINTENANCE_STATES={planned:'待批准保养',approved:'停机已批准',completed:'保养已完检'};
export const RESIN_STATES={available:'批次可用',quarantine:'批次隔离'};
export const MATERIAL_STATES={issued:'已领料',returned:'已登记退料'};
export const DELIVERY_STATES={dispatched:'已发样待签收',received:'客户已签收',accepted:'客户接受',rectification:'需整改重试',closed:'主管已关闭'};
