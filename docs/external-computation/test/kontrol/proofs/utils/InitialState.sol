// SPDX-License-Identifier: UNLICENSED
// This file was autogenerated by running `kontrol load-state`. Do not edit this file manually.

pragma solidity ^0.8.13;

import {Vm} from "forge-std/Vm.sol";

import {InitialStateCode} from "./InitialStateCode.sol";

contract InitialState is InitialStateCode {
    // Cheat code address, 0x7109709ECfa91a80626fF3989D68f67F5b1DD12D
    address private constant VM_ADDRESS = address(uint160(uint256(keccak256("hevm cheat code"))));
    Vm private constant vm = Vm(VM_ADDRESS);

    address internal constant counter8Address = 0x03A6a84cD762D9707A21605b548aaaB891562aAb;
    address internal constant counter6Address = 0x1d1499e622D69689cdf9004d05Ec547d650Ff211;
    address internal constant counter1Address = 0x2e234DAe75C793f67A35089C9d99245E1C58470b;
    address internal constant counter0Address = 0x5615dEB798BB3E4dFa0139dFa1b3D433Cc23b72f;
    address internal constant counter3Address = 0x5991A2dF15A8F6A256D3Ec51E99254Cd3fb576A9;
    address internal constant counter7Address = 0xA4AD4f68d0b91CFD19687c881e50f3A00242828c;
    address internal constant counter9Address = 0xD6BbDE9174b1CdAa358d2Cf4D57D1a9F7178FBfF;
    address internal constant counter2Address = 0xF62849F9A0B5Bf2913b396098F7c7019b51A820a;
    address internal constant counter5Address = 0xa0Cb889707d426A7A386870A03bc70d1b0697598;
    address internal constant counter4Address = 0xc7183455a4C133Ae270771860664b6B7ec320bB1;

    function recreateState() public {
        bytes32 slot;
        bytes32 value;
        vm.etch(counter0Address, counter0Code);
        vm.etch(counter1Address, counter1Code);
        slot = hex"0000000000000000000000000000000000000000000000000000000000000000";
        value = hex"0000000000000000000000000000000000000000000000000000000000000001";
        vm.store(counter1Address, slot, value);
        vm.etch(counter2Address, counter2Code);
        slot = hex"0000000000000000000000000000000000000000000000000000000000000000";
        value = hex"0000000000000000000000000000000000000000000000000000000000000002";
        vm.store(counter2Address, slot, value);
        vm.etch(counter3Address, counter3Code);
        slot = hex"0000000000000000000000000000000000000000000000000000000000000000";
        value = hex"0000000000000000000000000000000000000000000000000000000000000003";
        vm.store(counter3Address, slot, value);
        vm.etch(counter4Address, counter4Code);
        slot = hex"0000000000000000000000000000000000000000000000000000000000000000";
        value = hex"0000000000000000000000000000000000000000000000000000000000000004";
        vm.store(counter4Address, slot, value);
        vm.etch(counter5Address, counter5Code);
        slot = hex"0000000000000000000000000000000000000000000000000000000000000000";
        value = hex"0000000000000000000000000000000000000000000000000000000000000005";
        vm.store(counter5Address, slot, value);
        vm.etch(counter6Address, counter6Code);
        slot = hex"0000000000000000000000000000000000000000000000000000000000000000";
        value = hex"0000000000000000000000000000000000000000000000000000000000000006";
        vm.store(counter6Address, slot, value);
        vm.etch(counter7Address, counter7Code);
        slot = hex"0000000000000000000000000000000000000000000000000000000000000000";
        value = hex"0000000000000000000000000000000000000000000000000000000000000007";
        vm.store(counter7Address, slot, value);
        vm.etch(counter8Address, counter8Code);
        slot = hex"0000000000000000000000000000000000000000000000000000000000000000";
        value = hex"0000000000000000000000000000000000000000000000000000000000000008";
        vm.store(counter8Address, slot, value);
        vm.etch(counter9Address, counter9Code);
        slot = hex"0000000000000000000000000000000000000000000000000000000000000000";
        value = hex"0000000000000000000000000000000000000000000000000000000000000009";
        vm.store(counter9Address, slot, value);
    }
}