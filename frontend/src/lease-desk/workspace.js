import {billingPage} from './billing-page.js';
import {budgetPage} from './budget-page.js';
import {offersPage} from './offer-page.js';

const pages={
  'lease-budget':['让利预算',budgetPage],
  'lease-offers':['续租报价',offersPage],
  'lease-billing':['签约首账单',billingPage],
};
export const leaseLabels=Object.fromEntries(Object.entries(pages).map(([key,[label]])=>[key,label]));

export async function renderLease(main,key,user,refresh) {
  const [,handler]=pages[key];
  main.classList.add('lease-workspace');
  await handler(main,user,refresh);
}
